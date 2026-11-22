"""Small checks: SQL rule logic on a hand-made fixture, the real build, exports, docs numbers, xlsx, dashboard."""
import json
import pathlib

import duckdb
import polars as pl
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "paysim.duckdb"
EXP = ROOT / "exports"
FINDINGS = json.loads((ROOT / "docs" / "findings.json").read_text())
COLS = ["step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig", "nameDest",
        "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud"]


def run_sql_on(rows, tmp_path):
    df = pl.DataFrame(rows, schema=COLS, orient="row").with_row_index("tx_id", offset=1)
    pq = tmp_path / "tx.parquet"
    df.write_parquet(pq)
    con = duckdb.connect()
    con.execute(f"SET VARIABLE tx_parquet = '{pq.as_posix()}'")
    for f in sorted((ROOT / "sql").glob("0*.sql")):
        con.execute(f.read_text())
    return con


@pytest.fixture
def fixture_rows():
    rows = [
        # 1-2: fraud chain, same amount, transfer at step 3 and cash-out at step 4; victim drained
        (3, "TRANSFER", 5000.0, "C1", 5000.0, 0.0, "C2", 0.0, 0.0, 1, 0),
        (4, "CASH_OUT", 5000.0, "C3", 5000.0, 0.0, "C4", 100.0, 5100.0, 1, 0),
        # 3: normal payment at night (out of scope: PAYMENT)
        (2, "PAYMENT", 100.0, "C5", 1000.0, 900.0, "M1", 0.0, 0.0, 0, 0),
        # 4: normal transfer during the day, books balance, amount not equal to whole balance
        (14, "TRANSFER", 300.0, "C6", 1000.0, 700.0, "C7", 50.0, 350.0, 0, 0),
        # 5: cash-out of the same amount 2 hours after a transfer: NOT a chain (lag 2)
        (16, "CASH_OUT", 300.0, "C8", 400.0, 100.0, "C9", 0.0, 300.0, 0, 0),
        # 6-8: three inbound to C7 in one step -> dest velocity per hour
        (20, "CASH_OUT", 10.0, "C10", 100.0, 90.0, "C7", 350.0, 360.0, 0, 0),
        (20, "CASH_OUT", 11.0, "C11", 100.0, 89.0, "C7", 360.0, 371.0, 0, 0),
        (20, "CASH_OUT", 12.0, "C12", 100.0, 88.0, "C7", 371.0, 383.0, 0, 0),
        # 9: big transfer to a never-seen receiver -> new payee large + stated isFlaggedFraud rule
        (30, "TRANSFER", 250000.0, "C13", 300000.0, 50000.0, "C14", 0.0, 250000.0, 0, 1),
    ]
    return rows


def flags(con, col):
    return {r[0] for r in con.execute(f"SELECT tx_id FROM fct_alerts WHERE {col} ORDER BY 1").fetchall()}


def test_rules_on_fixture(fixture_rows, tmp_path):
    con = run_sql_on(fixture_rows, tmp_path)
    assert flags(con, "r07_chain_transfer_cashout") == {1, 2}           # both legs, lag 1 counts
    assert 4 not in flags(con, "r07_chain_transfer_cashout")            # lag 2 does not
    assert flags(con, "r08_full_drain") == {1, 2}
    assert flags(con, "r09_dest_balance_unchanged") == {1}
    assert flags(con, "r10_night_hours") == {1, 2}                       # PAYMENT at hour 2 is out of scope
    assert flags(con, "r02_velocity_dest_hour") == {6, 7, 8}
    assert 9 in flags(con, "r06_new_payee_large")
    assert flags(con, "b2_transfer_over_200k") == {9}
    assert flags(con, "b1_is_flagged_fraud") == {9}
    hour, day = con.execute("SELECT hour, day FROM stg_tx WHERE tx_id = 9").fetchall()[0]
    assert (hour, day) == (6, 1)


@pytest.mark.skipif(not DB.exists(), reason="needs `make data build`")
def test_full_build():
    con = duckdb.connect(str(DB), read_only=True)
    n, fraud, flagged, smin, smax = con.execute(
        "SELECT count(*), sum(is_fraud), sum(is_flagged_fraud), min(step), max(step) FROM stg_tx").fetchall()[0]
    assert (n, fraud, flagged, smin, smax) == (6_362_620, 8_213, 16, 1, 743)
    assert con.execute("SELECT count(DISTINCT tx_id) FROM fct_alerts").fetchall()[0][0] == n
    # fraud only appears in TRANSFER and CASH_OUT, which is why the monitoring scope is those two types
    assert con.execute("SELECT count(*) FROM stg_tx WHERE is_fraud = 1 AND NOT in_scope").fetchall()[0][0] == 0


def test_kaggle_size_matches_download_constant():
    meta = json.loads((ROOT / "docs" / "kaggle_dataset_metadata.json").read_text())
    import importlib.util
    spec = importlib.util.spec_from_file_location("dl", ROOT / "src" / "download.py")
    dl = importlib.util.module_from_spec(spec); spec.loader.exec_module(dl)
    assert meta["totalBytes"] == dl.SIZE
    assert meta["licenseName"] == "CC BY-SA 4.0"


def test_exports_consistent():
    r = pl.read_csv(EXP / "rule_metrics.csv")
    assert r.height == 12
    assert (r["true_positives"] <= r["alerts"]).all()
    fraud = FINDINGS["fraud"]
    for row in r.iter_rows(named=True):
        assert row["recall_pct"] == pytest.approx(100 * row["true_positives"] / fraud, abs=0.01)
        if row["alerts"]:
            assert row["precision_pct"] == pytest.approx(100 * row["true_positives"] / row["alerts"], abs=0.01)
    cube = pl.read_csv(EXP / "rule_combo_cube.csv")
    assert cube.filter(pl.col("is_fraud") == 1)["transactions"].sum() == fraud
    chain = cube.filter(pl.col("r07_chain_transfer_cashout"))["transactions"].sum()
    assert chain == FINDINGS["rules"]["r07_chain_transfer_cashout"]["alerts"]
    b = pl.read_csv(EXP / "alert_budget_curve.csv")
    assert b["recall_pct"].is_sorted()


def test_docs_numbers_come_from_findings():
    f = FINDINGS
    r7 = f["rules"]["r07_chain_transfer_cashout"]
    b1 = f["rules"]["b1_is_flagged_fraud"]
    must = [f"{f['rows']:,}", f"{f['fraud']:,}", f"{r7['recall_pct']}", f"{r7['precision_pct']}", f"{b1['recall_pct']}"]
    for doc in ("README.md", "MEMO.md", "LINKEDIN_POST.md"):
        text = (ROOT / doc).read_text()
        missing = [m for m in must if m not in text]
        assert not missing, f"{doc} is missing {missing}"


def test_tableau_extract():
    from openpyxl import load_workbook
    x = ROOT / "tableau" / "paysim_fraud_monitoring.xlsx"
    assert x.stat().st_size < 10 * 1024 * 1024
    wb = load_workbook(x, read_only=True)
    assert {"rules", "by_type", "by_hour", "budget", "chain_examples"} <= set(wb.sheetnames)
    assert (ROOT / "tableau" / "BUILD_SPEC.md").exists()


def test_dashboard_runs():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert len(at.metric) >= 5
