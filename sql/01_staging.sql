-- 01 staging: typed transactions + derived time and balance fields.
-- step = hour of the 30-day simulation (1..743). day = step // 24, hour of day = step % 24.
-- Monitoring scope used by every rule: TRANSFER and CASH_OUT (money leaving an account).
CREATE OR REPLACE TABLE stg_tx AS
SELECT
    tx_id,
    step,
    step // 24                                   AS day,
    step % 24                                    AS hour,
    type,
    amount,
    nameOrig                                     AS orig,
    oldbalanceOrg                                AS old_bal_orig,
    newbalanceOrig                               AS new_bal_orig,
    nameDest                                     AS dest,
    oldbalanceDest                               AS old_bal_dest,
    newbalanceDest                               AS new_bal_dest,
    isFraud                                      AS is_fraud,
    isFlaggedFraud                               AS is_flagged_fraud,
    type IN ('TRANSFER', 'CASH_OUT')             AS in_scope,
    left(nameDest, 1) = 'M'                      AS dest_is_merchant,
    -- how far the books are off after the transaction (0 = balances move exactly by the amount)
    round(old_bal_orig - amount - new_bal_orig, 2)  AS error_balance_orig,
    round(old_bal_dest + amount - new_bal_dest, 2)  AS error_balance_dest
FROM read_parquet(getvariable('tx_parquet'));

-- How often does an account show up? Needed to judge whether velocity rules can work at all.
CREATE OR REPLACE TABLE prof_account_counts AS
SELECT 'orig' AS side, n_tx, count(*) AS accounts
FROM (SELECT orig, count(*) AS n_tx FROM stg_tx GROUP BY orig) GROUP BY n_tx
UNION ALL
SELECT 'dest' AS side, n_tx, count(*) AS accounts
FROM (SELECT dest, count(*) AS n_tx FROM stg_tx GROUP BY dest) GROUP BY n_tx;
