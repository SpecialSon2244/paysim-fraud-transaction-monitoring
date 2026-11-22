"""Plotly figures shared by the Streamlit dashboard (app.py) and the static charts (src/charts.py).
Every figure is built from exports/*.csv, loaded with Polars."""
import pathlib

import plotly.graph_objects as go
import polars as pl
from plotly.subplots import make_subplots

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"
NAVY, TEAL, CORAL, SAND, GREY, LIGHT, ORANGE = "#264653", "#2A9D8F", "#E76F51", "#E9C46A", "#6C757D", "#CED4DA", "#F4A261"
FAMILY_COLOR = {"Velocity": SAND, "Amount": ORANGE, "Chain": TEAL, "Balance (leaky)": LIGHT,
                "Timing": NAVY, "Baseline": CORAL}
SOURCE = ("Data: PaySim synthetic mobile-money transactions (Lopez-Rojas et al. 2016), Kaggle ealaxi/paysim1, CC BY-SA 4.0. "
          "Synthetic data: no real customers.")
FONT = dict(family="Arial", size=13, color="#222")


def load(name: str) -> pl.DataFrame:
    return pl.read_csv(EXPORTS / f"{name}.csv")


def style(fig, title, subtitle="", h=520, w=1000, legend=True, source=True):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b><br><span style='font-size:13px;color:{GREY}'>{subtitle}</span>",
                   x=0.01, xanchor="left", y=0.97),
        font=FONT, height=h, width=w, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=70, r=40, t=100, b=(160 if legend else 90) if source else 60), showlegend=legend,
        legend=dict(orientation="h", y=-0.2, x=0, yanchor="top"),
    )
    if source:
        fig.add_annotation(text=SOURCE, xref="paper", yref="paper", x=0, y=-0.4 if legend else -0.15,
                           showarrow=False, font=dict(size=10, color=GREY), xanchor="left")
    fig.update_xaxes(showgrid=False, linecolor=LIGHT)
    fig.update_yaxes(gridcolor="#EEE", linecolor=LIGHT)
    return fig


def fraud_by_type():
    d = load("fraud_by_type")
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Transactions (millions)", "Fraud transactions"),
                        horizontal_spacing=0.12)
    colors = [CORAL if f > 0 else LIGHT for f in d["fraud"]]
    fig.add_bar(x=d["type"], y=d["transactions"] / 1e6, marker_color=colors, row=1, col=1,
                text=[f"{v/1e6:.2f}M" for v in d["transactions"]], textposition="outside", showlegend=False)
    fig.add_bar(x=d["type"], y=d["fraud"], marker_color=colors, row=1, col=1 + 1,
                text=[f"{f:,}<br>({r:.2f}%)" for f, r in zip(d["fraud"], d["fraud_rate_pct"])],
                textposition="outside", showlegend=False)
    fig.update_yaxes(range=[0, d["transactions"].max() / 1e6 * 1.2], row=1, col=1)
    fig.update_yaxes(range=[0, d["fraud"].max() * 1.3], row=1, col=2)
    tr = d.filter(pl.col("type") == "TRANSFER").row(0, named=True)
    co = d.filter(pl.col("type") == "CASH_OUT").row(0, named=True)
    return style(fig, "All fraud is in TRANSFER and CASH_OUT",
                 f"TRANSFER: {tr['fraud']:,} fraud ({tr['fraud_rate_pct']:.2f}% of transfers). "
                 f"CASH_OUT: {co['fraud']:,} ({co['fraud_rate_pct']:.2f}%). PAYMENT, CASH_IN and DEBIT: none.", legend=False)


POS = {"R07": "middle right", "R08": "middle left", "R04": "bottom center", "R10": "top center",
       "R02": "middle left", "R03": "top right", "R05": "top center", "B1": "middle right", "R09": "middle left"}


def rule_scatter(include_baselines=True):
    d = load("rule_metrics")
    if not include_baselines:
        d = d.filter(pl.col("family") != "Baseline")
    fig = go.Figure()
    for fam, g in d.group_by("family", maintain_order=True):
        fam = fam[0]
        fig.add_scatter(
            x=g["alerts_per_day"], y=g["recall_pct"], mode="markers+text", name=fam,
            marker=dict(size=16, color=FAMILY_COLOR[fam], opacity=0.9,
                        line=dict(color=NAVY if fam != "Balance (leaky)" else GREY, width=1),
                        symbol="diamond" if fam == "Balance (leaky)" else "circle"),
            text=[f"{r.split(' ', 1)[0]} · {p:.1f}%" for r, p in zip(g["rule"], g["precision_pct"])],
            textposition=[POS.get(r.split(" ", 1)[0], "top center") for r in g["rule"]], textfont=dict(size=11),
            customdata=g.select("rule", "precision_pct", "alerts").rows(),
            hovertemplate="%{customdata[0]}<br>Alerts/day %{x:,.1f}<br>Recall %{y:.1f}%<br>Precision %{customdata[1]:.2f}%"
                          "<br>Alerts %{customdata[2]:,}<extra></extra>")
    fig.update_xaxes(type="log", title="Alerts per day (log scale)", tickvals=[1, 10, 100, 1000, 10000],
                     ticktext=["1", "10", "100", "1,000", "10,000"], range=[-0.6, 4.5])
    fig.update_yaxes(title="Recall: share of all fraud caught (%)", range=[-5, 110])
    c = d.filter(pl.col("rule_id") == "r07_chain_transfer_cashout").row(0, named=True)
    return style(fig, "Rules: how much fraud they catch vs how many alerts they raise",
                 f"Label = precision. The chain rule R07 catches {c['recall_pct']:.1f}% "
                 f"of fraud at {c['alerts_per_day']:.0f} alerts/day. Diamonds = leaky balance rules.", h=600)


def fraud_by_hour():
    d = load("fraud_by_hour")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=d["hour"], y=d["transactions"], name="All transactions", marker_color=LIGHT)
    fig.add_scatter(x=d["hour"], y=d["fraud"], name="Fraud transactions", mode="lines+markers",
                    line=dict(color=CORAL, width=3), secondary_y=True)
    fig.add_vrect(x0=-0.5, x1=5.5, fillcolor=NAVY, opacity=0.07, line_width=0,
                  annotation_text="R10 window (0-5)", annotation_position="top left")
    fig.update_xaxes(title="Hour of day (step % 24)", dtick=1, range=[-0.6, 23.6])
    fig.update_yaxes(title="All transactions", secondary_y=False)
    fig.update_yaxes(title="Fraud transactions", secondary_y=True, range=[0, 500], dtick=100, showgrid=False)
    lo = d.sort("transactions").row(0, named=True)
    return style(fig, "Fraud runs around the clock; normal traffic does not",
                 f"Fraud is flat at {d['fraud'].min()} to {d['fraud'].max()} per hour of day. "
                 f"Normal volume drops to {lo['transactions']:,} at hour {lo['hour']}, so night-time fraud rates look extreme.")


def chain_example(i: int = 2):
    e = load("chain_examples").row(i, named=True)
    fig = go.Figure()
    boxes = [(0.02, 0.62, f"Victim account<br><b>{e['transfer_orig']}</b><br>balance {e['transfer_orig_balance_before']:,.0f} → {e['transfer_orig_balance_after']:,.0f}"),
             (0.62, 0.62, f"Receiving account<br><b>{e['transfer_dest']}</b>"),
             (0.02, 0.12, f"Cash-out sender<br><b>{e['cashout_orig']}</b><br>balance {e['cashout_orig_balance_before']:,.0f} → {e['cashout_orig_balance_after']:,.0f}"),
             (0.62, 0.12, f"Cash-out agent<br><b>{e['cashout_dest']}</b>")]
    for x, y, t in boxes:
        fig.add_shape(type="rect", x0=x, x1=x + 0.36, y0=y, y1=y + 0.26, line=dict(color=NAVY), fillcolor="#F4F7F8")
        fig.add_annotation(x=x + 0.18, y=y + 0.13, text=t, showarrow=False, font=dict(size=13))
    for y, label, col in [(0.75, f"TRANSFER {e['amount']:,.2f}<br>hour step {e['transfer_step']} · tx #{e['transfer_id']}", CORAL),
                          (0.25, f"CASH_OUT {e['amount']:,.2f}<br>hour step {e['cashout_step']} · tx #{e['cashout_id']}", CORAL)]:
        fig.add_annotation(x=0.615, y=y, ax=0.385, ay=y, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=2.5, arrowcolor=col, text="")
        fig.add_annotation(x=0.5, y=y + 0.07, text=label, showarrow=False, font=dict(size=12, color=col))
    fig.add_annotation(x=0.5, y=0.505, text="<b>R07 match:</b> same amount, same or next hour. "
                       "PaySim does not link the accounts, so amount + time is all the rule can use.",
                       showarrow=False, font=dict(size=12, color=NAVY))
    fig.update_xaxes(visible=False, range=[0, 1]); fig.update_yaxes(visible=False, range=[0.05, 0.95])
    return style(fig, "One fraud chain: take over, transfer out, cash out",
                 "Example from the data (both legs labelled isFraud = 1). Account IDs are synthetic.",
                 h=480, legend=False)


def budget_curve():
    d = load("alert_budget_curve")
    fig = go.Figure()
    fig.add_scatter(x=d["budget_per_day"], y=d["recall_pct"], name="Recall (fraud caught)", mode="lines+markers",
                    line=dict(color=TEAL, width=3))
    fig.add_scatter(x=d["budget_per_day"], y=d["precision_pct"], name="Precision (alerts that are fraud)",
                    mode="lines+markers", line=dict(color=CORAL, width=3))
    fig.update_xaxes(type="log", title="Alerts reviewed per day (queue ranked by rule score, then amount)",
                     tickvals=d["budget_per_day"].to_list())
    fig.update_yaxes(title="%", range=[0, 105])
    r = d.filter(pl.col("budget_per_day") == 300).row(0, named=True)
    r2 = d.filter(pl.col("budget_per_day") == 200).row(0, named=True)
    return style(fig, "Alert budget: what an analyst team gets for each extra alert",
                 f"200 alerts/day: {r2['recall_pct']:.1f}% of fraud caught at {r2['precision_pct']:.1f}% precision. "
                 f"300/day: {r['recall_pct']:.1f}% at {r['precision_pct']:.1f}%. Beyond that, almost only false alarms.")


def leakage_chart():
    d = load("leakage_check")
    cols = {"pct_amount_equals_sender_balance": "Amount = whole sender balance",
            "pct_sender_books_balance": "Sender balance moves exactly by amount",
            "pct_receiver_stays_zero": "Receiver balance 0 before and after"}
    fig = go.Figure()
    for v, name, col in [(1, "Fraud", CORAL), (0, "Not fraud", LIGHT)]:
        row = d.filter(pl.col("is_fraud") == v).row(0, named=True)
        fig.add_bar(y=list(cols.values()), x=[row[c] for c in cols], name=name, orientation="h", marker_color=col,
                    text=[f"{row[c]:.2f}%" for c in cols], textposition="outside")
    fig.update_xaxes(title="% of TRANSFER / CASH_OUT rows", range=[0, 115])
    fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"))
    return style(fig, "Why the balance rules are leaky",
                 "The simulator writes balances differently for fraud rows (the dataset notes say fraud is cancelled). "
                 "Near-perfect separation = a data artefact.", h=480)


def daily_volume():
    d = load("daily_volume")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=d["day"], y=d["transactions"], name="All transactions", marker_color=LIGHT)
    fig.add_scatter(x=d["day"], y=d["fraud"], name="Fraud transactions", mode="lines+markers",
                    line=dict(color=CORAL, width=3), secondary_y=True)
    fig.update_xaxes(title="Day of simulation (step // 24)", dtick=2)
    fig.update_yaxes(title="All transactions", secondary_y=False)
    fig.update_yaxes(title="Fraud transactions", secondary_y=True, range=[0, 400], dtick=100, showgrid=False)
    return style(fig, "Normal volume swings a lot; fraud stays flat",
                 f"Daily transactions range from {d['transactions'].min():,} to {d['transactions'].max():,}; "
                 f"fraud from {d['fraud'].min()} to {d['fraud'].max()} a day. Precision depends heavily on which days you look at.")
