#!/usr/bin/env python3
"""Generate a local HTML dashboard from a speedtester CSV log."""
import argparse
import csv
import datetime
import json
import sys
import webbrowser
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "report_template.html"


def load_rows(csv_path):
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.datetime.fromisoformat(row["timestamp"])
                server = ", ".join(
                    part for part in (row.get("server_name"), row.get("server_country")) if part
                )
                meta = " · ".join(part for part in (server, row.get("isp") or "") if part)
                rows.append({
                    "t": int(ts.timestamp() * 1000),
                    "d": float(row["download_mbps"]),
                    "u": float(row["upload_mbps"]),
                    "p": float(row["ping_ms"]),
                    "s": meta,
                })
            except (KeyError, ValueError):
                continue
    rows.sort(key=lambda r: r["t"])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i", "--csv", default="speedtest_log.csv",
        help="Input CSV path (default: speedtest_log.csv)",
    )
    parser.add_argument(
        "-o", "--out", default="speedtest_report.html",
        help="Output HTML path (default: speedtest_report.html)",
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Don't open the report in a browser after generating it",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"No CSV found at {csv_path}. Run speedtester.py first.", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(csv_path)
    template = TEMPLATE_PATH.read_text()
    html = (
        template
        .replace("__DATA_JSON__", json.dumps(rows))
        .replace("__GENERATED__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        .replace("__SOURCE__", csv_path.name)
    )

    out_path = Path(args.out)
    out_path.write_text(html)
    print(f"Wrote {out_path} ({len(rows)} readings)")

    if not args.no_open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
