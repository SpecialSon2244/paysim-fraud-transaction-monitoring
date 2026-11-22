"""Rule registry shared by evaluate.py, charts.py, the Tableau extract and app.py."""

RULES = [
    # column, short name, family, leaky?, plain-English definition
    ("r01_velocity_orig_day", "R01 Sender velocity (2+ tx/day)", "Velocity", False,
     "Sending account makes 2 or more transactions in the same day"),
    ("r02_velocity_dest_hour", "R02 Receiver velocity (3+ in/hour)", "Velocity", False,
     "Receiving account gets 3 or more incoming transactions in the same hour (step)"),
    ("r03_velocity_dest_day", "R03 Receiver velocity (10+ in/day)", "Velocity", False,
     "Receiving account gets 10 or more incoming transactions in the same day"),
    ("r04_amount_type_p99", "R04 Amount > p99 of type", "Amount", False,
     "Amount above the 99th percentile of its transaction type"),
    ("r05_amount_vs_dest_history", "R05 Amount > 5x receiver history", "Amount", False,
     "Receiver has 3+ earlier incoming transactions and the amount is more than 5x their mean"),
    ("r06_new_payee_large", "R06 New payee, amount >= 200k", "Amount", False,
     "Receiver never received money before in the data and the amount is 200,000 or more"),
    ("r07_chain_transfer_cashout", "R07 TRANSFER then CASH_OUT chain", "Chain", False,
     "TRANSFER and CASH_OUT of exactly the same amount in the same or next hour (both legs flagged)"),
    ("r08_full_drain", "R08 Sender balance drained to 0 (leaky)", "Balance (leaky)", True,
     "Amount equals the sender's whole balance and the balance ends at 0"),
    ("r09_dest_balance_unchanged", "R09 Receiver balance stays 0 (leaky)", "Balance (leaky)", True,
     "Customer receiver shows 0 before and 0 after although money was sent"),
    ("r10_night_hours", "R10 Night hours 0-5", "Timing", False,
     "TRANSFER or CASH_OUT with step % 24 between 0 and 5"),
    ("b1_is_flagged_fraud", "B1 Built-in isFlaggedFraud", "Baseline", False,
     "The simulator's own flag"),
    ("b2_transfer_over_200k", "B2 TRANSFER > 200k (stated flag rule)", "Baseline", False,
     "The rule the dataset description gives for isFlaggedFraud"),
]

SAFE = ["r04_amount_type_p99", "r05_amount_vs_dest_history", "r06_new_payee_large",
        "r07_chain_transfer_cashout", "r10_night_hours"]
SAFE_SUM = " + ".join(f"{c}::INT" for c in SAFE)

# Combined rule sets. Each is a SQL boolean expression on fct_alerts.
COMBINED = [
    ("C1 Chain + 1 more safe rule (priority queue)",
     "r07_chain_transfer_cashout AND (r04_amount_type_p99 OR r05_amount_vs_dest_history "
     "OR r06_new_payee_large OR r10_night_hours)"),
    ("C2 Chain rule alone (R07)", "r07_chain_transfer_cashout"),
    ("C2b Chain rule, amount below the 10,000,000 cap", "r07_chain_transfer_cashout AND amount < 10000000"),
    ("C3 Any 2+ safe rules", f"({SAFE_SUM}) >= 2"),
    ("C4 Chain OR amount p99 OR night", "r07_chain_transfer_cashout OR r04_amount_type_p99 OR r10_night_hours"),
    ("C5 Union of all safe rules", " OR ".join(SAFE)),
    ("C6 Union incl. leaky balance rules", " OR ".join(SAFE + ["r08_full_drain", "r09_dest_balance_unchanged"])),
]

# Priority score for the daily alert queue (safe rules only). The chain carries most weight.
SCORE_SQL = ("3 * r07_chain_transfer_cashout::INT + r04_amount_type_p99::INT + r05_amount_vs_dest_history::INT "
             "+ r06_new_payee_large::INT + r10_night_hours::INT")
BUDGETS = [25, 50, 100, 150, 200, 300, 400, 500, 1000, 2000]
