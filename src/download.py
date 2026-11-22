"""Download the PaySim CSV (Kaggle ealaxi/paysim1, 494 MB) from a public Hugging Face mirror.

The mirror (vitaliy-sharandin/synthetic-fraud-detection) holds the original Kaggle file
PS_20174392719_1491204439457_log.csv unchanged. We pin the mirror revision and check the
SHA-256 and the byte size. The size equals the totalBytes that Kaggle's public API reports
for ealaxi/paysim1 (493,534,783), see docs/kaggle_dataset_metadata.json.
No account or token is needed.
"""
import hashlib
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = "vitaliy-sharandin/synthetic-fraud-detection"
REVISION = "8ca94d2d0949e07d84224cdf057abfa35a03b59d"
FILE = "PS_20174392719_1491204439457_log.csv"
URL = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{FILE}"
SHA256 = "16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b"
SIZE = 493_534_783
OUT = ROOT / "data" / "raw" / FILE


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if OUT.exists() and OUT.stat().st_size == SIZE and sha256(OUT) == SHA256:
        print(f"{OUT.relative_to(ROOT)} already there, checksum ok")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".part")
    print(f"downloading {URL}")
    with requests.get(URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    if tmp.stat().st_size != SIZE or sha256(tmp) != SHA256:
        sys.exit("download does not match the expected size / SHA-256, stopping")
    tmp.rename(OUT)
    print(f"saved {OUT.relative_to(ROOT)} ({SIZE:,} bytes, checksum ok)")


if __name__ == "__main__":
    main()
