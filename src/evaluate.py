"""Evaluate every rule and combined rule set against isFraud; write exports/*.csv and docs/findings.json.

Precision = fraud alerts / alerts. Recall = fraud alerts / all fraud transactions.
Alerts per day = alerts / number of days in the data (31: day 0 = steps 1-23 ... day 30 = steps 720-743).
Periods: first half = days 0-15, second half = days 16-30 (thresholds were fixed before looking at either).
"""
import json
import os
import pathlib

import duckdb
import polars as pl

from rules import BUDGETS, COMBINED, RULES, SCORE_SQL

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
DB = ROOT / "data" / "paysim.duckdb"
EXP = ROOT / "exports"
EXP.mkdir(exist_ok=True)
PERIODS = {"all": "TRUE", "first_half": "day <= 15", "second_half": "day >= 16"}


def q(con, sql: str) -> pl.DataFrame:
    return con.sql(sql).pl()


def metrics(con, expr: str, n_days: int, fraud_total: dict) -> dict:
    out = {}
    for p, cond in PERIODS.items():
        a, tp = con.execute(
            f"SELECT count(*), coalesce(sum(is_fraud), 0) FROM fct_alerts WHERE ({expr}) AND {cond}").fetchall()[0]
        out[p] = (int(a), int(tp))
    a, tp = out["all"]
    fraud = fraud_total["all"]
    prec = tp / a if a else 0.0
    rec = tp / fraud
    row = {
        "alerts": a, "true_positives": tp, "false_positives": a - tp,
        "precision_pct": round(100 * prec, 2), "recall_pct": round(100 * rec, 2),
        "f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0,
        "alerts_per_day": round(a / n_days, 1),
    }
    for p in ("first_half", "second_half"):
        a_p, tp_p = out[p]
        row[f"precision_pct_{p}"] = round(100 * tp_p / a_p, 2) if a_p else None
        row[f"recall_pct_{p}"] = round(100 * tp_p / fraud_total[p], 2)
    return row


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    n_days = con.execute("SELECT count(DISTINCT day) FROM fct_alerts").fetchall()[0][0]
    fraud_total = {p: con.execute(f"SELECT sum(is_fraud) FROM fct_alerts WHERE {c}").fetchall()[0][0]
                   for p, c in PERIODS.items()}
    flag_tp = con.execute("SELECT sum(is_fraud) FROM fct_alerts WHERE b1_is_flagged_fraud").fetchall()[0][0]

    # 1. single rules
    rows = []
    for col, name, family, leaky, definition in RULES:
        m = metrics(con, col, n_days, fraud_total)
        m["extra_fraud_vs_isFlaggedFraud"] = con.execute(
            f"SELECT coalesce(sum(is_fraud), 0) FROM fct_alerts WHERE {col} AND NOT b1_is_flagged_fraud").fetchall()[0][0]
        rows.append({"rule_id": col, "rule": name, "family": family, "leaky": leaky, **m, "definition": definition})
    rule_df = pl.DataFrame(rows)
    rule_df.write_csv(EXP / "rule_metrics.csv")

    # 2. combined rule sets
    crow = [{"rule_set": name, **metrics(con, expr, n_days, fraud_total), "definition": expr} for name, expr in COMBINED]
    comb_df = pl.DataFrame(crow)
    comb_df.write_csv(EXP / "combined_metrics.csv")

    # 3. alert budget: per-day queue ranked by priority score, then amount
    con.execute(f"""
        CREATE TEMP TABLE ranked AS
        SELECT day, is_fraud, row_number() OVER (PARTITION BY day ORDER BY {SCORE_SQL} DESC, amount DESC, tx_id) AS rk
        FROM fct_alerts WHERE in_scope AND ({SCORE_SQL}) > 0""").fetchall()
    brow = []
    for b in BUDGETS:
        a, tp = con.execute(f"SELECT count(*), coalesce(sum(is_fraud),0) FROM ranked WHERE rk <= {b}").fetchall()[0]
        brow.append({"budget_per_day": b, "alerts": a, "true_positives": tp,
                     "precision_pct": round(100 * tp / a, 2), "recall_pct": round(100 * tp / fraud_total["all"], 2),
                     "alerts_per_day_actual": round(a / n_days, 1)})
    budget_df = pl.DataFrame(brow)
    budget_df.write_csv(EXP / "alert_budget_curve.csv")

    # 4. descriptive tables
    q(con, """SELECT type, count(*) AS transactions, sum(is_fraud) AS fraud, round(100.0*sum(is_fraud)/count(*), 3) AS fraud_rate_pct,
                     sum(is_flagged_fraud) AS flagged_by_isFlaggedFraud, round(sum(amount)/1e9, 2) AS amount_bn,
                     round(sum(CASE WHEN is_fraud=1 THEN amount ELSE 0 END)/1e9, 2) AS fraud_amount_bn
              FROM stg_tx GROUP BY type ORDER BY transactions DESC""").write_csv(EXP / "fraud_by_type.csv")
    q(con, """SELECT hour, count(*) AS transactions, sum(is_fraud) AS fraud,
                     round(100.0*sum(is_fraud)/count(*), 3) AS fraud_rate_pct,
                     sum(in_scope::INT) AS transfer_cashout, round(100.0*sum(is_fraud)/sum(in_scope::INT), 3) AS fraud_rate_in_scope_pct
              FROM stg_tx GROUP BY hour ORDER BY hour""").write_csv(EXP / "fraud_by_hour.csv")
    q(con, f"""SELECT day, count(*) AS transactions, sum(is_fraud) AS fraud,
                      sum(r07_chain_transfer_cashout::INT) AS chain_alerts,
                      sum((r07_chain_transfer_cashout AND is_fraud=1)::INT) AS chain_true_positives
               FROM fct_alerts GROUP BY day ORDER BY day""").write_csv(EXP / "daily_volume.csv")
    q(con, """SELECT side, n_tx, accounts FROM prof_account_counts ORDER BY side, n_tx""").write_csv(EXP / "account_counts.csv")
    q(con, """SELECT lag_steps, transfer_is_fraud, cashout_is_fraud, amount = 10000000 AS amount_is_10m, count(*) AS pairs
              FROM chain_pairs GROUP BY ALL ORDER BY ALL""").write_csv(EXP / "chain_pairs_summary.csv")
    q(con, """SELECT p.*, t.old_bal_orig AS transfer_orig_balance_before, t.new_bal_orig AS transfer_orig_balance_after,
                     c.old_bal_orig AS cashout_orig_balance_before, c.new_bal_orig AS cashout_orig_balance_after
              FROM chain_pairs p JOIN stg_tx t ON t.tx_id = p.transfer_id JOIN stg_tx c ON c.tx_id = p.cashout_id
              WHERE p.transfer_is_fraud = 1 AND p.cashout_is_fraud = 1 AND p.amount < 10000000
              ORDER BY p.transfer_step, p.transfer_id LIMIT 20""").write_csv(EXP / "chain_examples.csv")
    q(con, """SELECT is_fraud, count(*) AS transfer_cashout,
                     round(100.0*avg((error_balance_orig = 0)::INT), 2) AS pct_sender_books_balance,
                     round(100.0*avg((abs(amount - old_bal_orig) < 0.01)::INT), 2) AS pct_amount_equals_sender_balance,
                     round(100.0*avg((new_bal_orig = 0)::INT), 2) AS pct_sender_ends_at_zero,
                     round(100.0*avg((NOT dest_is_merchant AND old_bal_dest = 0 AND new_bal_dest = 0)::INT), 2) AS pct_receiver_stays_zero
              FROM stg_tx WHERE in_scope GROUP BY is_fraud ORDER BY is_fraud""").write_csv(EXP / "leakage_check.csv")

    # rule-combination cube for the dashboard's rule builder: one row per day x flag pattern x label
    flag_cols = ", ".join(c for c, *_ in RULES if c.startswith("r"))
    q(con, f"""SELECT day, {flag_cols}, is_fraud, count(*) AS transactions
               FROM fct_alerts WHERE in_scope GROUP BY ALL ORDER BY ALL""").write_csv(EXP / "rule_combo_cube.csv")

    # 5. headline numbers (every number in README / MEMO / post comes from here)
    acc = q(con, "SELECT side, sum(accounts) AS accounts, sum(CASE WHEN n_tx = 1 THEN accounts END) AS once, max(n_tx) AS max_tx FROM prof_account_counts GROUP BY side")
    accd = {r["side"]: r for r in acc.to_dicts()}
    tot = con.execute("SELECT count(*), sum(is_fraud), sum(is_flagged_fraud), min(step), max(step), sum(in_scope::INT) FROM stg_tx").fetchall()[0]
    r = {d["rule_id"]: d for d in rule_df.to_dicts()}
    c = {d["rule_set"]: d for d in comb_df.to_dicts()}
    fp10m = con.execute("""SELECT count(*) FROM fct_alerts WHERE r07_chain_transfer_cashout AND is_fraud = 0 AND amount = 10000000""").fetchall()[0][0]
    chain_fp = r["r07_chain_transfer_cashout"]["false_positives"]
    adj = con.execute("""SELECT count(*), sum((cashout_id = transfer_id + 1)::INT) FROM chain_pairs
                         WHERE transfer_is_fraud = 1 AND cashout_is_fraud = 1""").fetchall()[0]
    hours = q(con, "SELECT * FROM read_csv('exports/fraud_by_hour.csv')").to_dicts()
    night = con.execute("""SELECT sum(is_fraud), count(*) FROM stg_tx WHERE hour BETWEEN 0 AND 5""").fetchall()[0]
    findings = {
        "rows": tot[0], "fraud": int(tot[1]), "fraud_rate_pct": round(100 * tot[1] / tot[0], 3),
        "is_flagged_fraud": int(tot[2]), "flag_true_positives": int(flag_tp),
        "step_min": tot[3], "step_max": tot[4], "days": n_days, "transfer_cashout_rows": int(tot[5]),
        "fraud_first_half": int(fraud_total["first_half"]), "fraud_second_half": int(fraud_total["second_half"]),
        "orig_accounts": int(accd["orig"]["accounts"]), "orig_once_pct": round(100 * float(accd["orig"]["once"]) / float(accd["orig"]["accounts"]), 2),
        "orig_max_tx": int(accd["orig"]["max_tx"]),
        "dest_accounts": int(accd["dest"]["accounts"]), "dest_once_pct": round(100 * float(accd["dest"]["once"]) / float(accd["dest"]["accounts"]), 2),
        "dest_max_tx": int(accd["dest"]["max_tx"]),
        "chain_false_positives": int(chain_fp), "fraud_pairs": int(adj[0]), "fraud_pairs_next_row": int(adj[1]),
        "fraud_pairs_next_row_pct": round(100 * adj[1] / adj[0], 2),
        "chain_false_positives_amount_10m_pct": round(100 * fp10m / chain_fp, 2), "chain_false_positives_amount_10m": int(fp10m),
        "night_share_of_fraud_pct": round(100 * night[0] / tot[1], 2), "night_share_of_all_tx_pct": round(100 * night[1] / tot[0], 2),
        "fraud_rate_peak_hour": max(hours, key=lambda h: h["fraud_rate_pct"]),
        "fraud_rate_low_hour": min(hours, key=lambda h: h["fraud_rate_pct"]),
        "type_p99_amount": {t: round(v, 2) for t, v in con.execute("SELECT type, p99_amount FROM ref_type_amount").fetchall()},
        "r04_by_type": {t: {"alerts": a, "fraud": int(tp)} for t, a, tp in con.execute(
            "SELECT type, count(*), sum(is_fraud) FROM fct_alerts WHERE r04_amount_type_p99 GROUP BY type").fetchall()},
        "fraud_amount_zero": con.execute("SELECT count(*) FROM stg_tx WHERE is_fraud = 1 AND amount = 0").fetchall()[0][0],
        "rules": r, "combined": c, "budget": budget_df.to_dicts(),
    }
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "findings.json").write_text(json.dumps(findings, indent=2, default=str))

    with pl.Config(tbl_rows=30, tbl_cols=20, tbl_width_chars=220, fmt_str_lengths=45):
        print(rule_df.select("rule", "alerts", "true_positives", "precision_pct", "recall_pct", "alerts_per_day",
                             "precision_pct_first_half", "precision_pct_second_half", "extra_fraud_vs_isFlaggedFraud"))
        print(comb_df.drop("definition"))
        print(budget_df)
    con.close()


if __name__ == "__main__":
    main()
