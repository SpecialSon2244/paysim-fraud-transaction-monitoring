# LinkedIn post (draft, not posted)

A fraud flag that is right 100% of the time can still be useless. This week I did a transaction-monitoring take-home on PaySim, a synthetic mobile-money dataset: 6,362,620 transactions over one month, 8,213 of them fraud.

The built-in flag caught 16 of those 8,213. Every alert was correct, and recall was 0.19%.

So I wrote my own rules in DuckDB SQL (velocity, amount outliers, new payees, night-time activity, transfer-then-cash-out chains, balance checks) and measured each one on precision, recall and alerts per day.

What I found:
→ One rule did most of the work: a TRANSFER followed by a CASH_OUT of the same amount within an hour. It caught 99.27% of fraud at 77.71% precision, about 338 alerts a day.
→ Velocity rules were close to useless here, because 99.85% of senders appear only once in the data. Worth checking before writing the rule.
→ Two balance rules looked perfect, one at 100% precision. They are leaky: the simulator writes balances differently for fraud rows. I left them out.
→ With a ranked daily queue, reviewing 300 alerts a day caught 96.3% of fraud at 85.24% precision. Going from 300 to 500 a day added less than 1 point of recall.

The data is synthetic, and the fraud follows one scripted pattern, so these numbers are an upper bound. The memo covers the caveats and what I would test on real traffic.

Stack: DuckDB SQL, Polars, Plotly, Streamlit, pytest. One `make all` rebuilds everything.

Code, dashboard and memo: [REPO LINK]

Data: PaySim (Lopez-Rojas, Elmir, Axelsson 2016), Kaggle ealaxi/paysim1, CC BY-SA 4.0.

#DataAnalytics #SQL #FraudDetection #TransactionMonitoring #Fintech
