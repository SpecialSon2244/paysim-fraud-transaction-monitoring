-- 06 timing rule (R10): money out between hour 0 and 5 (step % 24 in 0..5), when normal volume is lowest.
CREATE OR REPLACE TABLE r_night_hours AS
SELECT tx_id FROM stg_tx WHERE in_scope AND hour BETWEEN 0 AND 5;
