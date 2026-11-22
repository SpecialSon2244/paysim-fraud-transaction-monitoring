"""Tidy Excel extract for Tableau Public web authoring -> tableau/paysim_fraud_monitoring.xlsx.

One sheet per chart, already aggregated (a few hundred rows in total). Percentages are numbers
from 0 to 100. See tableau/BUILD_SPEC.md for how each sheet is used.
"""
import json
import pathlib

import pandas as pd
import polars as pl

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXP = ROOT / "exports"
OUT = ROOT / "tableau" / "paysim_fraud_monitoring.xlsx"


def main() -> None:
    f = json.loads((ROOT / "docs" / "findings.json").read_text())
    kpi = pl.DataFrame({
        "Metric": ["Transactions", "Fraud transactions", "Fraud rate %", "Flagged by isFlaggedFraud",
                   "isFlaggedFraud recall %", "Chain rule R07 recall %", "Chain rule R07 precision %",
                   "Chain rule R07 alerts per day"],
        "Value": [float(v) for v in [f["rows"], f["fraud"], f["fraud_rate_pct"], f["is_flagged_fraud"],
                  f["rules"]["b1_is_flagged_fraud"]["recall_pct"],
                  f["rules"]["r07_chain_transfer_cashout"]["recall_pct"],
                  f["rules"]["r07_chain_transfer_cashout"]["precision_pct"],
                  f["rules"]["r07_chain_transfer_cashout"]["alerts_per_day"]]],
        "Order": list(range(1, 9)),
    })
    rules = pl.read_csv(EXP / "rule_metrics.csv").select(
        pl.col("rule").alias("Rule"), pl.col("family").alias("Family"),
        pl.when(pl.col("leaky")).then(pl.lit("Leaky")).otherwise(pl.lit("Usable")).alias("Leakage"),
        pl.col("alerts").alias("Alerts"), pl.col("true_positives").alias("Fraud caught"),
        pl.col("false_positives").alias("False alarms"),
        pl.col("precision_pct").alias("Precision %"), pl.col("recall_pct").alias("Recall %"),
        pl.col("alerts_per_day").alias("Alerts per day"),
        pl.col("precision_pct_first_half").alias("Precision % days 0-15"),
        pl.col("precision_pct_second_half").alias("Precision % days 16-30"),
        pl.col("definition").alias("Definition"))
    combined = pl.read_csv(EXP / "combined_metrics.csv").select(
        pl.col("rule_set").alias("Rule set"), pl.col("alerts").alias("Alerts"),
        pl.col("true_positives").alias("Fraud caught"), pl.col("precision_pct").alias("Precision %"),
        pl.col("recall_pct").alias("Recall %"), pl.col("alerts_per_day").alias("Alerts per day"))
    by_type = pl.read_csv(EXP / "fraud_by_type.csv").select(
        pl.col("type").alias("Type"), pl.col("transactions").alias("Transactions"), pl.col("fraud").alias("Fraud"),
        pl.col("fraud_rate_pct").alias("Fraud rate %"), pl.col("flagged_by_isFlaggedFraud").alias("isFlaggedFraud"),
        pl.when(pl.col("fraud") > 0).then(pl.lit("Has fraud")).otherwise(pl.lit("No fraud")).alias("Fraud present"))
    by_hour = pl.read_csv(EXP / "fraud_by_hour.csv").select(
        pl.col("hour").alias("Hour"), pl.col("transactions").alias("Transactions"), pl.col("fraud").alias("Fraud"),
        pl.col("fraud_rate_pct").alias("Fraud rate %"),
        pl.when(pl.col("hour") <= 5).then(pl.lit("Night 0-5")).otherwise(pl.lit("Day 6-23")).alias("Window"))
    daily = pl.read_csv(EXP / "daily_volume.csv").select(
        pl.col("day").alias("Day"), pl.col("transactions").alias("Transactions"), pl.col("fraud").alias("Fraud"),
        pl.col("chain_alerts").alias("Chain alerts"), pl.col("chain_true_positives").alias("Chain fraud caught"))
    budget = pl.read_csv(EXP / "alert_budget_curve.csv").select(
        pl.col("budget_per_day").alias("Alerts per day budget"), pl.col("recall_pct").alias("Recall %"),
        pl.col("precision_pct").alias("Precision %"), pl.col("alerts").alias("Alerts"),
        pl.col("true_positives").alias("Fraud caught"))
    lk = pl.read_csv(EXP / "leakage_check.csv")
    labels = {"pct_amount_equals_sender_balance": "Amount = whole sender balance",
              "pct_sender_books_balance": "Sender balance moves exactly by amount",
              "pct_receiver_stays_zero": "Receiver balance 0 before and after"}
    leakage = pl.concat([
        pl.DataFrame({"Check": [labels[c]], "Label": ["Fraud" if r["is_fraud"] else "Not fraud"], "Share %": [r[c]]})
        for r in lk.to_dicts() for c in labels])
    chain = pl.read_csv(EXP / "chain_examples.csv").select(
        pl.col("transfer_id").alias("Transfer tx"), pl.col("cashout_id").alias("Cash-out tx"),
        pl.col("transfer_step").alias("Transfer step"), pl.col("cashout_step").alias("Cash-out step"),
        pl.col("amount").alias("Amount"), pl.col("transfer_orig").alias("Victim account"),
        pl.col("transfer_dest").alias("Receiving account"), pl.col("cashout_orig").alias("Cash-out sender"),
        pl.col("cashout_dest").alias("Cash-out agent"))
    about = pl.DataFrame({"Note": [
        "PaySim synthetic mobile-money transactions (Lopez-Rojas, Elmir, Axelsson 2016), Kaggle ealaxi/paysim1, CC BY-SA 4.0.",
        "Synthetic data: simulated from one month of logs of a mobile-money service in an African country. No real customers.",
        f"{f['rows']:,} transactions, steps {f['step_min']} to {f['step_max']} (1 step = 1 hour), {f['days']} days.",
        "Percentages are numbers from 0 to 100. Leaky rules use balance columns that the simulator writes differently for fraud.",
        "This extract is a derivative of the PaySim data and is shared under CC BY-SA 4.0.",
    ]})
    sheets = {"about": about, "kpi": kpi, "rules": rules, "combined": combined, "by_type": by_type,
              "by_hour": by_hour, "daily": daily, "budget": budget, "leakage": leakage, "chain_examples": chain}
    OUT.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_pandas().to_excel(w, sheet_name=name, index=False)
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size/1024:.0f} KB, sheets: {', '.join(f'{k} ({v.height})' for k, v in sheets.items())}")


if __name__ == "__main__":
    main()
