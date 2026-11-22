-- 05 balance rules. LEAKY: the dataset notes say fraud transactions are cancelled, so the balance
-- columns of fraud rows were written differently by the simulator. These rules are evaluated to show
-- the effect, not recommended for production.
-- R08 full drain: the amount equals the sender's whole balance and the balance ends at 0.
-- R09 receiver balance unchanged: a customer receiver (not merchant) shows 0 before and 0 after
--     although a positive amount was sent to it.
CREATE OR REPLACE TABLE r_full_drain AS
SELECT tx_id FROM stg_tx
WHERE in_scope AND old_bal_orig > 0 AND abs(amount - old_bal_orig) < 0.01 AND new_bal_orig = 0;

CREATE OR REPLACE TABLE r_dest_balance_unchanged AS
SELECT tx_id FROM stg_tx
WHERE in_scope AND NOT dest_is_merchant AND amount > 0 AND old_bal_dest = 0 AND new_bal_dest = 0;
