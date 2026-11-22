"""Static PNG charts (Plotly + kaleido) -> docs/charts/."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures as F  # noqa: E402

OUT = F.ROOT / "docs" / "charts"
CHARTS = {
    "01_fraud_by_type": F.fraud_by_type,
    "02_rule_precision_recall_volume": F.rule_scatter,
    "03_fraud_by_hour": F.fraud_by_hour,
    "04_chain_example": F.chain_example,
    "05_alert_budget_curve": F.budget_curve,
    "06_leakage_check": F.leakage_chart,
    "07_daily_volume": F.daily_volume,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in CHARTS.items():
        make().write_image(OUT / f"{name}.png", scale=2)
        print(f"docs/charts/{name}.png")


if __name__ == "__main__":
    main()
