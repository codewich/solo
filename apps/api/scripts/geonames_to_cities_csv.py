#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
lqSnfA3v0347KHbi

CITIES_COLUMNS = [
    "id",
    "name",
    "asciiname",
    "alternatenames",
    "country_code",
    "country_name",
    "region",
    "feature_class",
    "feature_code",
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
    "timezone",
    "latitude",
    "longitude",
    "population",
    "dem",
    "geonames_modified_at",
]

EUROPE_COUNTRY_CODES = {
    "AD",
    "AL",
    "AT",
    "BA",
    "BE",
    "BG",
    "BY",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "IE",
    "IS",
    "IT",
    "LI",
    "LT",
    "LU",
    "LV",
    "MC",
    "MD",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SE",
    "SI",
    "SK",
    "SM",
    "UA",
    "VA",
    "XK",
}


def clean_int(value: str) -> str:
    return value if value.strip() else ""


def convert_row(columns: list[str]) -> dict[str, str] | None:
    if len(columns) < 19:
        return None

    country_code = columns[8].strip()
    return {
        "id": columns[0].strip(),
        "name": columns[1].strip() or columns[2].strip() or columns[0].strip(),
        "asciiname": columns[2].strip(),
        "alternatenames": columns[3].strip(),
        "country_code": country_code,
        "country_name": country_code,
        "region": columns[10].strip(),
        "feature_class": columns[6].strip(),
        "feature_code": columns[7].strip(),
        "admin1_code": columns[10].strip(),
        "admin2_code": columns[11].strip(),
        "admin3_code": columns[12].strip(),
        "admin4_code": columns[13].strip(),
        "timezone": columns[17].strip(),
        "latitude": columns[4].strip(),
        "longitude": columns[5].strip(),
        "population": clean_int(columns[14]),
        "dem": clean_int(columns[16]),
        "geonames_modified_at": columns[18].strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert GeoNames cities15000.txt TSV to a CSV matching public.cities."
    )
    parser.add_argument("input", type=Path, help="Path to cities15000.txt")
    parser.add_argument("output", type=Path, help="Output CSV path")
    parser.add_argument(
        "--scope",
        choices=["all", "europe"],
        default="europe",
        help="Country filter to apply before writing rows.",
    )
    args = parser.parse_args()

    row_count = 0
    with args.input.open("r", encoding="utf-8") as source, args.output.open(
        "w", encoding="utf-8", newline=""
    ) as target:
        writer = csv.DictWriter(target, fieldnames=CITIES_COLUMNS)
        writer.writeheader()

        for line in source:
            row = convert_row(line.rstrip("\n").split("\t"))
            if row is None:
                continue
            if args.scope == "europe" and row["country_code"] not in EUROPE_COUNTRY_CODES:
                continue
            writer.writerow(row)
            row_count += 1

    print(f"Wrote {row_count} city rows to {args.output}")


if __name__ == "__main__":
    main()
