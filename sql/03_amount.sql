-- 03 amount rules. No labels are used to set any threshold.
-- R04 amount above the 99th percentile of its own transaction type (percentile over all rows of that type).
-- R05 amount vs the receiving account's history: 3+ earlier incoming transactions and
--     amount > 5x their mean. (Sender history is not possible: senders appear once.)
-- R06 new payee, large amount: the receiving account has never received money before in the data
--     and the amount is 200,000 or more.
CREATE OR REPLACE TABLE ref_type_amount AS
SELECT type, quantile_cont(amount, 0.99) AS p99_amount, quantile_cont(amount, 0.5) AS median_amount, count(*) AS n
FROM stg_tx GROUP BY type;

CREATE OR REPLACE TABLE r_amount_type_p99 AS
SELECT t.tx_id FROM stg_tx t JOIN ref_type_amount r USING (type)
WHERE t.in_scope AND t.amount > r.p99_amount;

CREATE OR REPLACE TABLE stg_dest_history AS
SELECT tx_id,
       count(*)    OVER w AS prior_in_n,
       avg(amount) OVER w AS prior_in_mean
FROM stg_tx
WINDOW w AS (PARTITION BY dest ORDER BY step, tx_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING);

CREATE OR REPLACE TABLE r_amount_vs_dest_history AS
SELECT t.tx_id FROM stg_tx t JOIN stg_dest_history h USING (tx_id)
WHERE t.in_scope AND h.prior_in_n >= 3 AND t.amount > 5 * h.prior_in_mean;

CREATE OR REPLACE TABLE r_new_payee_large AS
SELECT t.tx_id FROM stg_tx t JOIN stg_dest_history h USING (tx_id)
WHERE t.in_scope AND h.prior_in_n = 0 AND t.amount >= 200000;
