-- 02 velocity rules.
-- R01 orig velocity: the sending account makes 2+ transactions in the same day.
--     In PaySim almost every nameOrig appears exactly once, so this rule can barely fire (see prof_account_counts).
-- R02 dest velocity (hour): the receiving account gets 3+ incoming transactions (any type) in the same step.
-- R03 dest velocity (day): the receiving account gets 10+ incoming transactions in the same day.
CREATE OR REPLACE TABLE r_velocity_orig_day AS
SELECT tx_id FROM (
    SELECT tx_id, in_scope, count(*) OVER (PARTITION BY orig, day) AS n_orig_day FROM stg_tx
) WHERE in_scope AND n_orig_day >= 2;

CREATE OR REPLACE TABLE r_velocity_dest_hour AS
SELECT tx_id FROM (
    SELECT tx_id, in_scope, count(*) OVER (PARTITION BY dest, step) AS n_dest_step FROM stg_tx
) WHERE in_scope AND n_dest_step >= 3;

CREATE OR REPLACE TABLE r_velocity_dest_day AS
SELECT tx_id FROM (
    SELECT tx_id, in_scope, count(*) OVER (PARTITION BY dest, day) AS n_dest_day FROM stg_tx
) WHERE in_scope AND n_dest_day >= 10;
