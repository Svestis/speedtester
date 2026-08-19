# speedtester

Periodically measures your internet upload/download speed and appends the
result to a local CSV file, so you can track your connection quality over
time.

## What it does

- Runs a speed test using [Ookla's official Speedtest CLI](https://www.speedtest.net/apps/cli)
  (the Speedtest.net network)
- Appends one row per test to a CSV file (created with a header on first run)
- Can run as a long-lived loop, or as a single `--once` invocation triggered
  by a scheduler
- Can auto-select the nearest server each run, or pin every test to one
  specific server ID for consistent, comparable results over time

CSV columns: `timestamp, download_mbps, upload_mbps, ping_ms, server_name, server_country, isp`

## Requirements

- Python 3.8+ (standard library only — no pip packages needed)
- [Ookla's Speedtest CLI](https://www.speedtest.net/apps/cli), a system binary

**Platform support:** developed and tested on macOS. The Python code
(`speedtester.py`, `report.py`) has no OS-specific logic and should work on
Linux and Windows too, but only macOS has actually been run in practice.
Windows setup steps are included below but are **untested** — if something
doesn't work, please open an issue.

## Setup

**macOS / Linux:**

```bash
git clone <this-repo-url>
cd speedtester
python3 -m venv .venv
brew tap teamookla/speedtest
brew install speedtest
```

(No Homebrew on Linux? Download the CLI for your distro directly from
[speedtest.net/apps/cli](https://www.speedtest.net/apps/cli) instead of the
`brew` step.)

**Windows** *(untested)*:

```powershell
git clone <this-repo-url>
cd speedtester
python -m venv .venv
```

Then download the Windows build from
[speedtest.net/apps/cli](https://www.speedtest.net/apps/cli), unzip it, and
add the folder containing `speedtest.exe` to your PATH (**System Properties
→ Environment Variables → Path**) so plain `speedtest` resolves from any
terminal — that's how `speedtester.py` invokes it.

The first run of `speedtest` prompts you to accept Ookla's license and GDPR
notice; `speedtester.py` passes `--accept-license --accept-gdpr` automatically
so it won't block on that after the first run.

> Commands throughout the rest of this README use the macOS/Linux venv path,
> `.venv/bin/python`. On Windows, substitute `.venv\Scripts\python.exe`.

> **Why the official CLI and not the `speedtest-cli` PyPI package?** This
> project originally used the (now largely unmaintained) `speedtest-cli`
> Python package. In practice its server-list fetching turned out to be
> broken against the current Speedtest.net API — it would silently fall back
> to a tiny, wrong pool of servers (observed: 10 servers, all on a different
> continent from the actual connection), producing wildly inconsistent
> results and bogus multi-minute "ping" readings. Ookla's own CLI is actively
> maintained and doesn't have this problem.

## Usage

Run continuously, testing every 15 minutes (default), logging to
`speedtest_log.csv` in the current directory:

```bash
.venv/bin/python speedtester.py
```

Custom interval and log path:

```bash
.venv/bin/python speedtester.py --interval 30 --csv ~/Documents/speedtest_log.csv
```

Single test, then exit (useful for scheduler-driven setups):

```bash
.venv/bin/python speedtester.py --once
```

Press `Ctrl+C` to stop the loop cleanly (it finishes the in-progress test
first).

**Pin to a specific server** instead of auto-selecting the "best" one each
run:

```bash
speedtest -L                                          # list nearby servers and their IDs
.venv/bin/python speedtester.py --server-id 12345
```

Auto-selection re-evaluates the "best" server every single run, which can
jump between servers — sometimes even between countries, if the server list
your Speedtest CLI receives is incomplete or your ISP's IP geolocation is off
— making results hard to compare over time. Pinning to one server (ideally
one operated by your own ISP, if it has one — check for it in the `-L`
output) gives consistent, comparable data, which matters if you're using
these logs as evidence of a real connection problem rather than just casual
monitoring.

## Running it continuously

There are a few ways to keep this running, depending on your platform and
whether you want it tied to an IDE session or fully backgrounded.

### Option A: the built-in loop

Just run `speedtester.py` (no `--once`) in a terminal, tmux/screen session,
or your IDE. Simplest option, but it stops when that process is killed.

### Option B: PyCharm

Open the project folder in PyCharm and accept the `.venv` interpreter when
prompted (or set it manually under **Settings → Project → Python
Interpreter**). Then create your own run configuration: **Run → Edit
Configurations → + → Python**, set the script to `speedtester.py` and
parameters to e.g. `--interval 15`, then Run. This runs in the foreground of
PyCharm's Run panel, so it stops if PyCharm closes.

(A ready-made run configuration used to be checked into this repo, but isn't
anymore — pinning it to a specific `--server-id` would mean committing a
value that indirectly reveals your ISP and approximate location. Keep any
run configuration with a server ID in it **unshared**/local-only — in
PyCharm's Edit Configurations dialog, uncheck "Store as project file" — so
it never ends up in a commit. See [Privacy & security](#privacy--security).)

### Option C: launchd (macOS background service)

For a background service that keeps running independent of any IDE or
terminal, and survives logout/reboot, use the included installer:

```bash
scripts/install_launchd.sh --interval 15 --server-id 12345
```

(`--server-id` is optional — omit it to auto-select each run.)

This generates a `launchd` agent from the template in `launchd/`, using
paths specific to your machine (nothing personal is hardcoded in the repo
itself — the template is filled in locally at install time), and loads it
with `launchctl`. It runs `speedtester.py --once` on the given interval,
logging stdout/stderr to `logs/`.

To remove it:

```bash
scripts/uninstall_launchd.sh
```

### Option D: cron (Linux) / Task Scheduler (Windows)

On Linux, a cron entry or systemd timer running `speedtester.py --once` on
your desired interval works the same way launchd does on macOS.

On Windows *(untested)*, `schtasks` can do the same:

```powershell
schtasks /create /tn "Speedtester" /tr "\"C:\path\to\speedtester\.venv\Scripts\python.exe\" \"C:\path\to\speedtester\speedtester.py\" --once" /sc minute /mo 15
```

Adjust the paths and `/mo 15` (minutes) for your setup. To remove it:

```powershell
schtasks /delete /tn "Speedtester" /f
```

Unlike `install_launchd.sh`, there's no installer script for cron or Task
Scheduler yet — these are the raw commands, not a maintained wrapper.

**Note:** don't run more than one of these against the same CSV file at the
same time — each writer appends independently, so you'd get duplicate rows
rather than corruption, but it's redundant. Pick one as your "always on"
logger (launchd is the natural choice) and use the others for ad hoc runs,
or point them at different `--csv` paths.

## Viewing the data

Generate a local HTML dashboard from the CSV — stat tiles, download/upload
and ping charts, date-range filters, and a sortable data table — and open it
in your browser:

```bash
.venv/bin/python report.py
```

Custom input/output paths, or skip auto-opening the browser:

```bash
.venv/bin/python report.py --csv speedtest_log.csv --out speedtest_report.html --no-open
```

The report is a single self-contained HTML file (`speedtest_report.html` by
default) — no server, no external scripts or fonts, works offline. It's
git-ignored for the same reason as the CSV: it embeds your personal speed
history.

## Privacy & security

- No API keys or accounts are required — the Speedtest CLI talks directly to
  public Speedtest.net infrastructure. It does send Ookla the license/GDPR
  acceptance and standard Speedtest telemetry (IP, approximate location) as
  part of any test — see [Ookla's privacy policy](https://www.speedtest.net/about/privacy)
  if that matters to you.
- The CSV output and `logs/` directory are git-ignored by default, since
  they contain your personal network usage history (timestamps, ISP name,
  measured speeds). Nothing in this repo transmits that data anywhere
  except to your own local file.
- The launchd template contains no personal paths or usernames; those are
  filled in on your machine by `scripts/install_launchd.sh` and never
  committed.

## License

MIT — see [LICENSE](LICENSE).
