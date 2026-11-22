# Alert-triage memo: which monitoring rules to keep

**To:** Head of Fraud & Risk · **From:** Analytics · **Data:** PaySim synthetic mobile-money transactions,
6,362,620 rows over 31 days, 8,213 labelled fraud (0.129%). Synthetic data, see caveats. Details and SQL:
[README.md](README.md).

## Bottom line

1. **Our current flag (`isFlaggedFraud`) misses almost everything.** It caught 16 of 8,213 fraud transactions
   (0.19% recall). Every alert was right, but that does not help when 99.8% of fraud goes through.
2. **One rule does most of the work:** a TRANSFER followed by a CASH_OUT of the same amount within an hour (R07).
   It catches 99.27% of fraud at 77.71% precision, about 338 alerts a day.
3. **Run it as a ranked daily queue of about 300 alerts.** At 300 a day we catch 96.3% of fraud with 85.24% of alerts
   being real. At 200 a day it is 72.7% caught at 96.31% precision. Above 300 a day the extra alerts are almost all
   false alarms (500 a day: 97.15% caught, 52.22% precision).

## What I recommend

| # | Decision | Threshold | Evidence |
|---|---|---|---|
| 1 | **Keep R07** (TRANSFER → CASH_OUT chain) as the core rule | same amount, cash-out in the same or next hour | 99.27% recall, 77.71% precision, 338.4 alerts/day |
| 2 | **Keep R04 (amount > p99 of type), R06 (new payee ≥ 200k), R05 and R10 (hours 0-5) only as score points**, not as standalone alerts | score = 3 × chain + 1 per other hit, ties broken by amount | Alone they run at 0.83% to 7.28% precision and 800 to 5,155 alerts/day |
| 3 | **Set the daily review budget at about 300**, re-check monthly | top 300 per day by score | 96.3% recall, 85.24% precision |
| 4 | **Investigate the 10,000,000 amount** before adding any rule on it | — | 90.85% of R07's 2,338 false positives are at exactly 10,000,000. Without that amount, R07 would be at 97.35% precision and 95.77% recall, but I picked that cut after seeing the labels |
| 5 | **Drop velocity rules R01 to R03 for now** (keep the SQL) | — | 99.85% of senders appear once; receiver velocity is at 0.05% to 0.09% precision. Revisit on real data where customers repeat |
| 6 | **Do not use balance-based rules R08 and R09** | — | The balance columns are written differently for fraud (the dataset notes say fraud is cancelled). R08 shows 100% precision for that reason only, and adds 0 fraud on top of the safe rules |
| 7 | **Replace the TRANSFER > 200k flag** | — | 13,197.1 alerts/day at 0.67% precision and 33.36% recall |

## Alert budget trade-off

| Alerts per day | 100 | 200 | 300 | 500 | 1,000 |
|---|---:|---:|---:|---:|---:|
| Fraud caught (recall) | 37.11% | 72.7% | 96.3% | 97.15% | 97.18% |
| Alerts that are fraud (precision) | 98.32% | 96.31% | 85.24% | 52.22% | 27.85% |

Fraud runs at 220 to 316 transactions a day, so a queue much smaller than that cannot reach high recall however good
the ranking is.

## What I am not sure about

- **Synthetic data.** All fraud follows one scripted pattern with exact amounts, and 94.59% of fraud pairs sit in
  consecutive rows of the log. Real mules split amounts, add delays and use more accounts, so R07's numbers are an
  upper bound. Before using it for real I would test a looser match (amount within a few percent, a longer window,
  account links where we have them).
- **Precision moves with normal volume.** Normal traffic ranges from 282 to 571,039 transactions a day while fraud is
  flat, so R07 runs at 64.74% precision in days 0-15 and 99.09% in days 16-30. Budget and thresholds should be
  checked on a busy month.
- **No real out-of-time test.** One simulated month only; the two halves of the month are the closest I have.
- **Labels are perfect and instant here.** In production they arrive late (chargebacks, customer reports), which
  lowers measured precision at first and delays any tuning.
