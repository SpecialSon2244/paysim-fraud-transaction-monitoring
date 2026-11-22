-- 04 TRANSFER -> CASH_OUT chains (R07).
-- A TRANSFER followed by a CASH_OUT of exactly the same amount in the same or the next step.
-- PaySim does not link the two legs by account (the CASH_OUT sender is not the TRANSFER receiver),
-- so the match is on amount and time only. Both legs are flagged.
CREATE OR REPLACE TABLE chain_pairs AS
SELECT t.tx_id AS transfer_id, c.tx_id AS cashout_id,
       t.step AS transfer_step, c.step AS cashout_step, c.step - t.step AS lag_steps,
       t.amount, t.orig AS transfer_orig, t.dest AS transfer_dest, c.orig AS cashout_orig, c.dest AS cashout_dest,
       t.is_fraud AS transfer_is_fraud, c.is_fraud AS cashout_is_fraud,
       t.dest = c.orig AS same_account_link
FROM stg_tx t
JOIN stg_tx c
  ON c.type = 'CASH_OUT' AND c.amount = t.amount AND c.step BETWEEN t.step AND t.step + 1
WHERE t.type = 'TRANSFER' AND t.amount > 0;

CREATE OR REPLACE TABLE r_chain_transfer_cashout AS
SELECT transfer_id AS tx_id FROM chain_pairs
UNION
SELECT cashout_id AS tx_id FROM chain_pairs;
