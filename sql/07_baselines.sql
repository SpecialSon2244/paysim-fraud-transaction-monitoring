-- 07 baselines.
-- B1 the simulator's own flag isFlaggedFraud.
-- B2 the business rule the dataset describes for that flag: a TRANSFER above 200,000.
CREATE OR REPLACE TABLE b_is_flagged_fraud AS SELECT tx_id FROM stg_tx WHERE is_flagged_fraud = 1;
CREATE OR REPLACE TABLE b_transfer_over_200k AS SELECT tx_id FROM stg_tx WHERE type = 'TRANSFER' AND amount > 200000;
