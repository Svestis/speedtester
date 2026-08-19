#!/usr/bin/env python3
"""Periodically measure internet upload/download speed and log to CSV."""
import argparse
import csv
import datetime
import json
import os
import signal
import subprocess
import sys
import time

CSV_FIELDS = [
    "timestamp",
    "download_mbps",
    "upload_mbps",
    "ping_ms",
    "server_name",
    "server_country",
    "isp",
]


def run_speedtest(server_id=None):
    cmd = ["speedtest", "--accept-license", "--accept-gdpr", "--format=json"]
    if server_id:
        cmd += ["--server-id", str(server_id)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        message = proc.stderr.strip()
        for line in reversed(proc.stdout.strip().splitlines()):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = parsed.get("error") or parsed.get("message") or message
            break
        raise RuntimeError(message or f"speedtest exited with code {proc.returncode}")
    result = json.loads(proc.stdout)
    server = result["server"]
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "download_mbps": round(result["download"]["bandwidth"] * 8 / 1_000_000, 2),
        "upload_mbps": round(result["upload"]["bandwidth"] * 8 / 1_000_000, 2),
        "ping_ms": round(result["ping"]["latency"], 2),
        "server_name": f"{server['name']} ({server['location']})",
        "server_country": server["country"],
        "isp": result["isp"],
    }


def append_to_csv(path, row):
    file_exists = os.path.isfile(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i", "--interval", type=float, default=15,
        help="Minutes between tests (default: 15)",
    )
    parser.add_argument(
        "-o", "--csv", default="speedtest_log.csv",
        help="Path to CSV log file (default: speedtest_log.csv)",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single test and exit instead of looping",
    )
    parser.add_argument(
        "--server-id", type=int, default=None,
        help="Pin every test to a specific Speedtest server ID instead of "
             "auto-selecting each run (run `speedtest -L` to list nearby "
             "server IDs). Recommended for tracking trends over time, since "
             "auto-selection can jump between servers run to run.",
    )
    args = parser.parse_args()

    running = True

    def handle_sigint(signum, frame):
        nonlocal running
        running = False
        print("\nStopping after current test...")

    signal.signal(signal.SIGINT, handle_sigint)

    while running:
        try:
            row = run_speedtest(args.server_id)
            append_to_csv(args.csv, row)
            print(
                f"{row['timestamp']}  down={row['download_mbps']} Mbps  "
                f"up={row['upload_mbps']} Mbps  ping={row['ping_ms']} ms  "
                f"server={row['server_name']}"
            )
        except FileNotFoundError:
            print(
                "speedtest CLI not found. Install it with:\n"
                "  brew tap teamookla/speedtest && brew install speedtest",
                file=sys.stderr,
            )
        except (RuntimeError, json.JSONDecodeError, KeyError, subprocess.TimeoutExpired) as exc:
            print(f"speedtest failed, skipping this reading: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"unexpected error: {exc}", file=sys.stderr)

        if args.once or not running:
            break

        for _ in range(int(args.interval * 60)):
            if not running:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
