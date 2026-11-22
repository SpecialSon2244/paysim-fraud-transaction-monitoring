"""Streamlit dashboard: PaySim transaction monitoring (rule-based fraud flags and alert budget).

Reads only exports/*.csv and docs/findings.json (committed), so it runs on a fresh clone: streamlit run app.py
"""
import json
import pathlib
import sys

import polars as pl
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import figures as F  # noqa: E402
from rules import RULES  # noqa: E402

st.set_page_config(page_title="PaySim transaction monitoring", layout="wide")


@st.cache_data
def data(name: str) -> pl.DataFrame:
    return F.load(name)


@st.cache_data
def findings() -> dict:
    return json.loads((ROOT / "docs" / "findings.json").read_text())


def show(fig):
    fig.update_layout(width=None)
    st.plotly_chart(fig, width="stretch")


f = findings()
st.title("Transaction monitoring on PaySim: which rules are worth an analyst's time?")
st.caption(F.SOURCE + " One step = one hour; 31 days. All numbers come from the SQL rules in sql/ and src/evaluate.py.")

k = st.columns(5)
k[0].metric("Transactions", f"{f['rows']:,}")
k[1].metric("Fraud transactions", f"{f['fraud']:,}", f"{f['fraud_rate_pct']}% of all", delta_color="off")
k[2].metric("isFlaggedFraud catches", f"{f['flag_true_positives']} of {f['fraud']:,}",
            f"{f['rules']['b1_is_flagged_fraud']['recall_pct']}% recall", delta_color="off")
r7 = f["rules"]["r07_chain_transfer_cashout"]
k[3].metric("Chain rule R07 recall", f"{r7['recall_pct']}%", f"{r7['precision_pct']}% precision", delta_color="off")
k[4].metric("R07 alerts per day", f"{r7['alerts_per_day']:,.0f}")

tab_rules, tab_build, tab_budget, tab_patterns, tab_chain, tab_leak = st.tabs(
    ["Rule scorecard", "Rule builder", "Alert budget", "Fraud patterns", "Chain example", "Leakage check"])

with tab_rules:
    show(F.rule_scatter())
    rm = data("rule_metrics")
    st.dataframe(rm.select("rule", "family", "leaky", "alerts", "true_positives", "precision_pct", "recall_pct",
                           "alerts_per_day", "precision_pct_first_half", "precision_pct_second_half",
                           "extra_fraud_vs_isFlaggedFraud", "definition"), hide_index=True, width="stretch")
    st.subheader("Combined rule sets")
    st.dataframe(data("combined_metrics"), hide_index=True, width="stretch")

with tab_build:
    st.write("Pick rules and how many of them must fire. Computed from a cube of TRANSFER and CASH_OUT "
             "transactions grouped by rule flags and day (exports/rule_combo_cube.csv).")
    cube = data("rule_combo_cube")
    names = {c: n for c, n, *_ in RULES if c.startswith("r")}
    default = ["r07_chain_transfer_cashout", "r04_amount_type_p99"]
    pick = st.multiselect("Rules", list(names), default=default, format_func=lambda c: names[c])
    need = st.slider("Alert when at least this many picked rules fire", 1, max(len(pick), 1), 1)
    days = st.slider("Days", 0, 30, (0, 30))
    if pick:
        hits = sum(pl.col(c).cast(pl.Int32) for c in pick)
        c = cube.filter(pl.col("day").is_between(*days)).with_columns(alert=hits >= need)
        tot_fraud = c.filter(pl.col("is_fraud") == 1)["transactions"].sum()
        a = c.filter(pl.col("alert"))
        n_alerts = a["transactions"].sum()
        tp = a.filter(pl.col("is_fraud") == 1)["transactions"].sum()
        n_days = days[1] - days[0] + 1
        m = st.columns(4)
        m[0].metric("Alerts", f"{n_alerts:,}")
        m[1].metric("Alerts per day", f"{n_alerts / n_days:,.1f}")
        m[2].metric("Precision", f"{100 * tp / n_alerts:.2f}%" if n_alerts else "n/a")
        m[3].metric("Recall", f"{100 * tp / tot_fraud:.2f}%" if tot_fraud else "n/a")
        if any(c in pick for c in ("r08_full_drain", "r09_dest_balance_unchanged")):
            st.warning("R08 and R09 use balance columns that are leaky in PaySim (see the Leakage check tab).")

with tab_budget:
    show(F.budget_curve())
    st.dataframe(data("alert_budget_curve"), hide_index=True, width="stretch")
    st.caption("Each day, in-scope transactions with at least one safe rule hit are ranked by score "
               "(3 x chain + amount p99 + receiver history + new payee + night), then by amount. "
               "The team reviews the top N per day.")

with tab_patterns:
    show(F.fraud_by_type())
    show(F.fraud_by_hour())
    show(F.daily_volume())

with tab_chain:
    show(F.chain_example())
    st.dataframe(data("chain_examples"), hide_index=True, width="stretch")
    st.dataframe(data("chain_pairs_summary"), hide_index=True)

with tab_leak:
    show(F.leakage_chart())
    st.write("The Kaggle dataset notes say fraud transactions are cancelled, so the balance columns "
             "(oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest) should not be used for detection. "
             "R08 and R09 are shown only to make that visible.")
    st.dataframe(data("leakage_check"), hide_index=True)
    st.dataframe(data("account_counts").filter(pl.col("n_tx") <= 10), hide_index=True)
