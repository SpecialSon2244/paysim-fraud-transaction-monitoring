-- 08 one row per transaction with every rule flag (FALSE when a rule did not fire).
CREATE OR REPLACE TABLE fct_alerts AS
SELECT
    t.tx_id, t.step, t.day, t.hour, t.type, t.amount, t.in_scope, t.is_fraud, t.is_flagged_fraud,
    t.tx_id IN (SELECT tx_id FROM r_velocity_orig_day)      AS r01_velocity_orig_day,
    t.tx_id IN (SELECT tx_id FROM r_velocity_dest_hour)     AS r02_velocity_dest_hour,
    t.tx_id IN (SELECT tx_id FROM r_velocity_dest_day)      AS r03_velocity_dest_day,
    t.tx_id IN (SELECT tx_id FROM r_amount_type_p99)        AS r04_amount_type_p99,
    t.tx_id IN (SELECT tx_id FROM r_amount_vs_dest_history) AS r05_amount_vs_dest_history,
    t.tx_id IN (SELECT tx_id FROM r_new_payee_large)        AS r06_new_payee_large,
    t.tx_id IN (SELECT tx_id FROM r_chain_transfer_cashout) AS r07_chain_transfer_cashout,
    t.tx_id IN (SELECT tx_id FROM r_full_drain)             AS r08_full_drain,
    t.tx_id IN (SELECT tx_id FROM r_dest_balance_unchanged) AS r09_dest_balance_unchanged,
    t.tx_id IN (SELECT tx_id FROM r_night_hours)            AS r10_night_hours,
    t.tx_id IN (SELECT tx_id FROM b_is_flagged_fraud)       AS b1_is_flagged_fraud,
    t.tx_id IN (SELECT tx_id FROM b_transfer_over_200k)     AS b2_transfer_over_200k
FROM stg_tx t;
