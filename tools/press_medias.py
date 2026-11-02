"""Press-media table: data/press_medias.csv (the file you edit) → .parquet.

Rebuild with `python -m tools.press_medias`. The CSV holds one row per media; the builder checks the
enum columns and unique ids, derives `region` from `country`, and writes the parquet.
"""

import csv
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

CSV = Path("data/press_medias.csv")
PARQUET = CSV.with_suffix(".parquet")

ENUMS = {
    "kind": {"press", "tv_radio", "video", "podcast", "newsletter", "think_tank", "institution", "fact_check"},
    "topic": {"general", "economy", "ecology", "science_tech", "politics", "geopolitics", "philosophy"},
    "orientation": {"left", "center", "right", "public_service", "institutional", "state_media", "unknown"},
    "access": {"free", "partial", "paywalled"},
}
REGIONS = {
    "france": "FR",
    "europe": "BE CH DE GB",
    "north_america": "CA US",
    "asia": "BD CN HK ID IN JP KR PH PK SG",
    "middle_east": "EG IL QA TR",
    "africa": "KE NG ZA",
    "latin_america": "AR BR UY",
    "oceania": "AU NZ",
}
_REGION_OF = {c: r for r, cs in REGIONS.items() for c in cs.split()}
COLUMNS = ["id", "name", "kind", "topic", "orientation", "country", "region", "language", "access",
           "access_note", "feed_slug", "url", "notes", "verified_on"]


def load(path: Path = CSV) -> list[dict]:
    """The rows, validated, with `region` derived (`international` when there is no country)."""
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate ids: {sorted({i for i in ids if ids.count(i) > 1})}")
    for r in rows:
        for col, allowed in ENUMS.items():
            if r[col] not in allowed:
                raise ValueError(f"{r['id']}: {col}={r[col]!r} not in {sorted(allowed)}")
        if r["country"] and r["country"] not in _REGION_OF:
            raise ValueError(f"{r['id']}: country {r['country']!r} has no region (add it to REGIONS)")
        r["region"] = _REGION_OF.get(r["country"], "international")
    return rows


def build(csv_path: Path = CSV) -> int:
    rows = load(csv_path)
    schema = pa.schema([(c, pa.date32() if c == "verified_on" else pa.string()) for c in COLUMNS])
    for r in rows:
        r["verified_on"] = date.fromisoformat(r["verified_on"]) if r["verified_on"] else None
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), csv_path.with_suffix(".parquet"))
    return len(rows)


if __name__ == "__main__":
    print(f"{build()} rows → {PARQUET}")
