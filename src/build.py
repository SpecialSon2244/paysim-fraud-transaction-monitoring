"""Polars staging + DuckDB SQL rules.

1. Polars reads the PaySim CSV, adds tx_id (the row number in the original file, 1-based) and
   writes data/staging/transactions.parquet.
2. DuckDB runs sql/01_staging.sql ... sql/0N_*.sql in order into data/paysim.duckdb.
   Every rule lives in SQL; Python only orchestrates.
"""
import os
import pathlib
import time

import duckdb
import polars as pl

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
CSV = ROOT / "data" / "raw" / "PS_20174392719_1491204439457_log.csv"
PARQUET = ROOT / "data" / "staging" / "transactions.parquet"
DB = ROOT / "data" / "paysim.duckdb"
SQL_FILES = sorted((ROOT / "sql").glob("0*.sql"))


def stage() -> None:
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    df = pl.read_csv(CSV, schema_overrides={"step": pl.Int32, "isFraud": pl.Int8, "isFlaggedFraud": pl.Int8})
    df = df.with_row_index("tx_id", offset=1)
    df.write_parquet(PARQUET, compression="zstd")
    print(f"staged {df.height:,} transactions -> {PARQUET.relative_to(ROOT)} ({time.time() - t:.0f}s)")


def build() -> None:
    DB.unlink(missing_ok=True)
    con = duckdb.connect(str(DB))
    con.execute("SET memory_limit = '6GB'")
    con.execute(f"SET VARIABLE tx_parquet = '{PARQUET.as_posix()}'")
    for f in SQL_FILES:
        t = time.time()
        con.execute(f.read_text())
        print(f"ran {f.name} ({time.time() - t:.1f}s)")
    for tbl in ("stg_tx", "chain_pairs", "fct_alerts"):
        print(f"  {tbl}: {con.execute(f'SELECT count(*) FROM {tbl}').fetchone()[0]:,} rows")
    con.close()


if __name__ == "__main__":
    if not PARQUET.exists() or PARQUET.stat().st_mtime < CSV.stat().st_mtime:
        stage()
    build()
