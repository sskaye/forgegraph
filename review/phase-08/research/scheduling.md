# Research: scheduling and freshness (phase 8)

Input for the phase 8 proposal. Read first: architecture D7, D11, D12, D13; decisions.md phase 1 (structured conditions instead of expression strings) and phase 4 (DataFrame/Parquet input; scheduling only renders); build-plan Phase 8.

Two things in the project docs pull against each other and the proposal has to settle them:

- D12 says "There's no separate job format": flags on `job install` (`--every "day 06:00" --out ~/Dashboards`).
- The build plan's Phase 8 opens with "the schedule spec, a further kind (cadence, the status file, `on_failure`)".

This report recommends the build plan's version, a schedule file (section 6).

---

## 1. OS schedulers driven from a CLI

### 1.1 macOS: launchd (LaunchAgents)

| Topic | Finding | Source |
|---|---|---|
| Where | Per-user agents go in `~/Library/LaunchAgents`. The plist is named `<Label>.plist`, and `Label` is required and must be unique. | [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |
| Keys | `ProgramArguments` is the argv. Also `EnvironmentVariables`, `WorkingDirectory`, and `StandardOutPath`/`StandardErrorPath` (files that stdout/stderr go to). `RunAtLoad` defaults to false, and the man page advises against using it. | [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |
| Calendar vs interval | `StartCalendarInterval` works like crontab, and missing keys are wildcards. It can be an array of dicts, so any finite set of times can be listed. `StartInterval` runs are missed while the Mac is asleep ("shortcomings in kqueue(3)"). **Use StartCalendarInterval for everything, and write "every N minutes" as a list of minutes.** | [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |
| Sleep / off | Asleep: the job "will run when the computer wakes up", and missed runs are "coalesced into one event". Powered off: the job "does not execute until the next designated time". | [Apple, Scheduling Timed Jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html), [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |
| launchctl | `load`/`unload` are deprecated. The man page's recommended replacements are `bootstrap`, `bootout`, `enable` and `disable`. Domain target `gui/<uid>`, e.g. `launchctl bootstrap gui/501 ~/Library/LaunchAgents/x.plist`. `kickstart` runs a service now, ignoring its launch conditions: this is the "run once through the real scheduler" step. `print` shows the last exit status, but its output "is not an API". | [launchctl(1)](https://keith.github.io/xcode-man-pages/launchctl.1.html) |
| Cron on macOS | Apple: cron "has been deprecated in favor of launchd", and "you should not programmatically add a cron job". | [Apple, Scheduling Timed Jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html) |
| PATH | Jobs get a minimal PATH (`/usr/bin:/bin:/usr/sbin:/sbin`), with no Homebrew directories and no shell profile. Fix: absolute paths, or `PATH` in `EnvironmentVariables`. (Community sources; Apple doesn't document the default.) | [flaviocopes](https://flaviocopes.com/courses/automate-macos/control-environment-and-output/), [gitlab-runner #3463](https://gitlab.com/gitlab-org/gitlab-runner/issues/3463) |
| Privacy (TCC) | A background job reading or writing Desktop, Documents, Downloads or cloud-synced folders can fail with "Operation not permitted" until the binary that launchd runs (the Python interpreter) gets Full Disk Access. A grant to the terminal app doesn't carry over, and no public API can add the grant. This matches D12's caveat. | [Apple Developer Forums 118508](https://developer.apple.com/forums/thread/118508), [teratail 322393](https://teratail.com/questions/322393) |
| Background Items | Since macOS 13, adding a LaunchAgent posts a "Background Items Added" notification and lists the agent under Login Items, where the user can switch it off without deleting the plist. | [eclecticlight](https://eclecticlight.co/2023/02/15/controlling-login-and-background-items-in-ventura/), [mjtsai](https://mjtsai.com/blog/2022/07/28/ventura-notifies-user-of-new-login-items) |
| Logs | stdout/stderr go to the `StandardOutPath` files. launchd doesn't rotate them. | [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |
| Time zone | The man page has no time-zone key, so jobs run in system local time. | [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) |

### 1.2 Linux: cron

| Topic | Finding | Source |
|---|---|---|
| Environment | `SHELL=/bin/sh`. `HOME` and `LOGNAME` come from passwd. Debian's cron sets `PATH=/usr/bin:/bin`, and variables can be set inside the crontab. A `%` in a command becomes a newline unless escaped. `MAILTO` mails the output. | [crontab(5) man7](https://man7.org/linux/man-pages/man5/crontab.5.html), [crontab(5) Debian](https://manpages.debian.org/testing/cron/crontab.5) |
| Syntax | Five fields, plus `@daily` and the like. When both day-of-month and day-of-week are restricted, a day matching **either** runs the job. | [crontab(5) man7](https://man7.org/linux/man-pages/man5/crontab.5.html) |
| Time zone / DST | `CRON_TZ` sets the table's time zone (cronie). Times skipped by a DST change never run, and repeated times run twice. | [crontab(5) man7](https://man7.org/linux/man-pages/man5/crontab.5.html) |
| Missed runs | Jobs due while the machine is off or asleep don't run until the next scheduled time (anacron exists for daily and longer jobs). | [Apple, Scheduling Timed Jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html) |
| Safe editing | `crontab -l`, change only a block marked with comments, write back with `crontab -`. python-crontab does the same, and finds jobs by comment. | [python-crontab](https://pypi.org/project/python-crontab/) |
| Run now | cron has no "run this entry now". To prove a job "through the real scheduler", install a one-off line for the next minute and wait up to about 60 s. | (follows from the crontab(5) model) |
| Availability | Arch installs no cron by default, because the base system uses systemd timers. | [ArchWiki Cron](https://wiki.archlinux.org/title/Cron) (via search; page blocked to fetch), [Arch FS#38255](https://bugs.archlinux.org/task/38255) |

### 1.3 Linux: systemd user timers

| Topic | Finding | Source |
|---|---|---|
| OnCalendar | Wall-clock timers. Shorthands `daily`, `weekly`, `hourly` and so on. An optional time zone suffix (`UTC` or an IANA name). `systemd-analyze calendar` normalizes an expression and prints its next run. | [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html), [systemd.time(7)](https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html) |
| Missed runs | `Persistent=true` stores the last trigger time on disk, so a run missed while the machine was off fires at the next activation. It works only with OnCalendar. `AccuracySec` defaults to 1 min. `WakeSystem` needs privileges. | [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) |
| Failure hook | `OnFailure=` starts other units when this one enters "failed"; `OnSuccess=` exists since v249. | [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) |
| Environment | Set with `Environment=` and `EnvironmentFile=` in the service. `ExecSearchPath=` applies when no PATH is given. | [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) |
| Logged-out runs | The user manager normally starts at first login. `loginctl enable-linger` starts it at boot and keeps it after logout. | [loginctl(1)](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html), [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) |
| Run now | `systemctl --user start forgegraph-<name>.service` runs the same unit the timer runs, a true proof run. | (systemd standard) |

**Is systemd preferable to cron on Linux?** For this use, yes:

- runs missed while the machine was off are caught up (`Persistent`);
- a proof run goes through the real unit;
- the journal keeps the logs;
- `OnFailure` is built in;
- `systemd-analyze` validates the cadence;
- some distributions ship no cron.

Cron stays the fallback where there is no systemd user manager (WSL without systemd, containers, the BSDs). The build plan names cron; whether to switch is decision Q2.

### 1.4 Windows Task Scheduler

| Topic | Finding | Source |
|---|---|---|
| Create | `schtasks /create /xml <file> /tn \ForgeGraph\<name> /f`. A `\Folder\name` task name keeps ForgeGraph's tasks together, which makes `list` easy. `/f` replaces an existing task. | [schtasks create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create) |
| Run now | `schtasks /run` "ignores the schedule" and doesn't change the next run time. | [schtasks run](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-run) |
| Logged off | LogonType `InteractiveToken`: runs only while the user is logged on, no password. `S4U`: runs logged off, no stored password, "no access to the network or encrypted files". `Password`: stores the password. `/np` = no password stored, local resources only. | [LogonType](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-logontype-principaltype-element), [schtasks create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create) |
| Missed runs | `StartWhenAvailable=true` starts the task "any time after its scheduled time has passed". The default is false. | [StartWhenAvailable](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-startwhenavailable-settingstype-element) |
| Laptop pitfall | `DisallowStartIfOnBatteries` defaults to **true**: on battery, a task doesn't start at all unless ForgeGraph sets this to false. | [DisallowStartIfOnBatteries](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-disallowstartifonbatteries-settingstype-element) |
| Overlap | `MultipleInstancesPolicy` defaults to `IgnoreNew`, so no second instance starts while one runs. | [MultipleInstancesPolicy](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-multipleinstancespolicy-settingstype-element) |
| Timeout | `ExecutionTimeLimit` is an ISO 8601 duration; `PT0S` means no limit. | [ExecutionTimeLimit](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-executiontimelimit-settingstype-element) |
| Diagnostics | schtasks doesn't check that the program path exists ("the task is created, but it won't run"). | [schtasks create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create) |

Untested; needs a check in CI: `python.exe` may flash a console window under InteractiveToken, and `pythonw.exe` would avoid it.

### 1.5 Python libraries

| Library | What it is | Fit |
|---|---|---|
| [python-crontab](https://pypi.org/project/python-crontab/) 3.4.0, LGPL-3 | Reads and writes user crontabs. Finds jobs by comment. `CronSlices.is_valid()` validates expressions. On Windows it handles crontab files only. | Covers the cron backend only. Small gain for the size of the dependency. |
| [APScheduler](https://apscheduler.readthedocs.io/en/3.x/userguide.html) | An in-process scheduler (thread or process pools) with `misfire_grace_time` and `coalesce`. | Needs a long-running Python process. D12 rejects that: the OS scheduler runs the job. |
| [schedule](https://schedule.readthedocs.io/en/stable/) | An "in-process scheduler for periodic jobs" with an English-like API (`every().day.at("10:30")`). Its docs say not to use it when jobs must persist or timing must be exact. | Same objection. |
| [croniter](https://pypi.org/project/croniter/) 6.2.4, MIT, pallets-eco | Computes next and previous run times of a cron expression; time zones via aware datetimes. | Useful in tests, and needed only if the cadence accepts cron strings. |

No maintained library installs launchd, systemd, Task Scheduler and cron jobs from one interface (searched; none found). **Recommendation: write the four backends directly; each is small.**

- launchd: stdlib [`plistlib`](https://docs.python.org/3/library/plistlib.html) plus `launchctl`.
- systemd: two text units plus `systemctl --user`.
- Task Scheduler: an XML file plus `schtasks`.
- cron: `crontab -l` / `crontab -` with a marked block.

Add no runtime dependency. croniter can be a test-only dependency if cron output is checked by next-run times.

---

## 2. Cadence syntax

| Option | Validation | Maps to launchd / cron / systemd / Task Scheduler / GHA & Claude (cron) | Notes |
|---|---|---|---|
| Cron 5-field | Needs a parser (python-crontab or croniter) | cron: yes. launchd: expand every field to lists and write one dict per combination (feasible). systemd: yes, except the either-day rule, since OnCalendar requires both day fields to match. Task Scheduler: only simple patterns. | Users and agents know it, and GHA and Claude take cron. Day-of-month OR day-of-week semantics are a trap ([crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html)). |
| systemd OnCalendar | `systemd-analyze` exists on Linux only | Richer than cron (seconds, `~` from month end), so it can't map back to cron or launchd in general. | [systemd.time(7)](https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html) |
| RFC 5545 RRULE | Needs a parser (dateutil) | Richer still (BYSETPOS, COUNT/UNTIL). The time zone comes from DTSTART's TZID. | [RFC 5545 §3.3.10](https://datatracker.ietf.org/doc/html/rfc5545#section-3.3.10). Overkill. |
| Human string ("daily at 07:00") | Needs a grammar | Whatever subset you define | A parser in all but name. |
| **Structured fields (recommended)** | **Ranges only, no parser** | Exactly, if the set of forms is restricted (below) | Same reasoning as the phase 1 decision: "Structured conditions need no parser" (decisions.md). |

**Recommended v1 forms.** Each maps exactly to all four OS schedulers and to a cron string for the GHA and Claude recipes:

- `every: hour` with `at: ":MM"`, or `every: minutes` with `interval` dividing 60.
  - launchd: a list of `Minute` dicts.
  - Task Scheduler: a daily trigger with `Repetition`.
  - systemd: `*:MM`.
- `every: day` with `at: "HH:MM"`, optionally limited to weekdays with `days: [mon, tue, …]`.
- `every: week` on one or more weekdays at `HH:MM`.
- `every: month` on a day of the month from 1 to 28 at `HH:MM`. Days 29–31 aren't offered: Task Scheduler skips short months ([schtasks create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create)).

**Time zones.** launchd has no time zone key, so local time is the only zone every OS backend shares. cron's `CRON_TZ` is cronie-specific. systemd and GHA accept IANA zones ([GHA timezone key](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)). Claude tasks use local time ([scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)).

Recommendation:

- Times are the machine's local time, with no time zone parameter in v1.
- The status file and stamps record times as ISO 8601 with a UTC offset.
- The GHA recipe either converts the time to UTC or uses the `timezone:` key.
- The docs and the skill warn against 01:00–03:00 local, where cron runs DST-skipped times never and repeated times twice ([crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html)).

---

## 3. Status and failure conventions

**Monitoring services.** All three below assume the job reports in, and alert on silence:

- **healthchecks.io.** A check has a period plus a grace time, or a cron or OnCalendar schedule plus grace. Pings go to `/start`, `/fail` or `/<exit-status>`, and silence past the grace time means "down" ([docs](https://healthchecks.io/docs/), [bash](https://healthchecks.io/docs/bash/)).
- **Cronitor.** Pings carry `state=run|complete|fail`, `status_code`, `metric=count|duration|error_count` and `message` ([telemetry API](https://cronitor.io/docs/telemetry-api)).
- **Dead Man's Snitch** follows the same check-in-or-alert model.

**What to record** (Prometheus batch-job guidance): "The key metric of a batch job is the last time it succeeded", plus the last completion (success or failure), the duration and the records processed ([Prometheus instrumentation](https://prometheus.io/docs/practices/instrumentation/)).

**Failure hooks:**

- systemd `OnFailure=` ([systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html));
- GitHub Actions `if: ${{ failure() }}` ([expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions));
- cron `MAILTO` ([crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html)).

ForgeGraph's own `on_failure` should run inside `forgegraph job run`, so it behaves the same on every scheduler and in the cloud recipes.

**Exit codes.** The scheduler's own record (launchctl print, systemctl, schtasks "Last Result") only sees the exit code. So: 0 when every target rendered, non-zero otherwise.

**Recommended status file.** JSON, written atomically (write a temp file, then [`os.replace`](https://docs.python.org/3/library/os.html#os.replace)), and kept small:

- `job`, `schedule_file`, `cadence` (normalized), `scheduler` (launchd|systemd|cron|task_scheduler), `forgegraph_version`, `host`;
- `last_attempt`: `started_at`, `finished_at`, `duration_s`, `result` (success|failure), `exit_code`;
- `last_success`: `finished_at`;
- `consecutive_failures`;
- per target: `file`, `outputs` (paths), `rows` (read, plotted, dropped, as in D13), `data_files` (`path`, `mtime`, `size`), `data_as_of`, `lint_issues` (count), `error` (`problem`, `parameter`, `message`, in the same shape as `--json` problems);
- `on_failure`: `command`, `ran_at`, `exit_code`.

**Logs.** launchd doesn't rotate its stdout files. Have `job run` write its own log with [RotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler). Point the scheduler's stdout/stderr at one small file, which catches crashes before Python starts. On systemd, the journal is enough.

**Overlap.** Task Scheduler (`IgnoreNew`) and systemd don't start a second instance while one runs; cron does. Add a lock file in `job run` for all backends.

---

## 4. Data freshness indicators

**Precedents:**

- **Tableau** inserts a "Data Update Time" field into titles and captions. With a live connection it shows the refresh time, not when the source changed ([Tableau KB](https://kb.tableau.com/articles/en_US/HowTo/adding-data-refresh-time-stamp-to-view)).
- **Power BI's** common "last refreshed" card is a query that returns now(). It shows that the refresh ran, not that the data changed: "If the SQL refresh fails but the Last Refreshed Date query still runs, the report will still appear updated" ([Perficient](https://blogs.perficient.com/2022/08/24/how-to-show-last-refresh-date-in-power-bi/)). This is the argument for stamping the data's time, not the render time.
- **dbt source freshness** has `warn_after` and `error_after` (`{count, period}`). Freshness is measured from `loaded_at_field` (a timestamp column), or from warehouse metadata when there is none ([dbt freshness](https://docs.getdbt.com/reference/resource-properties/freshness)).
- **Grafana:** no first-party "data as of" feature was found. The usual approach is a Stat panel with the "From Now" unit on the latest timestamp, with thresholds mapped to "Stale" (community sources: [OneUptime](https://oneuptime.com/blog/post/2025-12-17-show-x-time-ago-grafana-influxdb/view), [Grafana community](https://community.grafana.com/t/grafana-7-stat-panel-time-of-last-point/30634)).

**mtime vs a timestamp column.**

- The file's mtime is cheap and general: it says when the file was written.
- It overstates freshness when a file is copied without preserving timestamps. GNU `cp` keeps them only with `--preserve=timestamps` ([cp invocation](https://www.gnu.org/software/coreutils/manual/html_node/cp-invocation.html)).
- It can't tell rewritten-but-old rows from new ones.
- A timestamp column (dbt's `loaded_at_field`) measures the data itself, but needs the user to name a column.
- Recommendation: mtime, as the build plan says. A `freshness.column` option can come later, as Q6.

**One threshold covers both failures.** The stamp shows data age, so a page left over from a job that stopped and a page from a job that runs on stale Parquet both show old data. Stale when `now − data_as_of > stale_after`.

- Following healthchecks (period plus grace), the default `auto` is one cadence period plus a grace.
- Example: a daily job gives 24 h + 25% = 30 h. A tight threshold (24 h) would flag a daily dashboard as stale just before each run.

**Static image vs HTML.**

| Output | Freshness shown |
|---|---|
| PNG/PDF | Only the stamp, drawn into the figure: "Data as of 2026-10-21 05:12 +01:00 · updated daily 06:00" (D12: the stamp "carries the expected cadence"). Small text in a margin, above lint's 6 pt floor. |
| Layouts | One stamp with the **oldest** `data_as_of` across tiles (conservative). The status file keeps each tile's. |
| HTML | The page embeds `data_as_of` and `stale_after`. A small script compares them with `Date.now()` and shows a banner when stale. A simulated clock test injects the clock. File-sharing previews often don't run scripts (D12), so the in-image stamp is the one that always shows. |

The stamp is drawn from data mtime, not the render clock, so `SOURCE_DATE_EPOCH` determinism (D13) still holds.

---

## 5. Cloud and agent alternatives

**GitHub Actions `schedule`** ([events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)):

- UTC by default, with an optional IANA `timezone:` key (`- cron: '30 5 * * 1-5'` then `timezone: "America/New_York"`);
- minimum interval 5 min;
- delayed under load, and queued jobs may be dropped; the top of the hour is busiest;
- runs on the latest commit of the default branch;
- in public repos, disabled after 60 days without repository activity;
- notifications go to whoever last edited the cron line.

The recipe runs `forgegraph job run` (or `render`) on files in the repo, uploads or commits the outputs, and adds an `if: failure()` step. The Parquet files must be in the repo or fetched by the user's own step.

**Claude scheduled tasks** ([compare](https://code.claude.com/docs/en/scheduled-tasks)):

- **Cloud** ([cloud tasks](https://code.claude.com/docs/en/routines); formerly routines; research preview):
  - runs on Anthropic infrastructure on a fresh clone, with no local files;
  - minimum 1 h;
  - pushes to `claude/` branches;
  - a green run status "does not mean the work your prompt describes succeeded";
  - counts against subscription usage.
- **Desktop** ([desktop tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks)):
  - runs locally with local files, but only while the app is open and the machine awake;
  - after sleep, one catch-up run for the most recent missed time within 7 days;
  - a per-task permission mode, and a run stalls on an unapproved tool;
  - stored in `~/.claude/scheduled-tasks/<name>/SKILL.md`.
- **`/loop` / CronCreate** (session tasks): session-scoped, expire after 7 days, no catch-up. Not suitable.

For a deterministic render, the OS scheduler is cheaper and more reliable than an agent run. A Claude task earns its place only when an agent should look at the result or prepare data (data prep is out of ForgeGraph's scope).

---

## 6. Recommended schedule spec and CLI

### 6.1 The spec (a further kind, in the house style)

```yaml
name: lab_dashboard          # [text]; The name of the schedule. Names the scheduler entry and the status file.
version: 0          # [int]; The version number of the specification.
description: Lab throughput dashboard, rendered every morning.          # [text]; The description of the schedule.
extends: None          # [None, schedule]; Each parameter not listed is inherited from this schedule. If None, this file must list every parameter.

fixed_parameters: None          # List of fixed parameters for the schedule, None if none.

variable_parameters:          # List of variable parameters for the schedule, None if none.
    targets:
        files: [lab.layout.yaml]          # [graphspecs, layouts]; GraphSpec and layout files rendered on each run: absolute, starting with ~, or relative to this file's folder.
        output_folder: ~/Dashboards          # [None, text]; Folder the outputs are saved in. None: beside each target file.
    cadence:
        every: day          # [minutes, hour, day, week, month]; How often the job runs, in the machine's local time.
        interval: 1          # [positive int]; For every: minutes, the minutes between runs; must divide 60. Otherwise 1.
        at: "06:00"          # [None, time]; Time of day, HH:MM, 24-hour; for every: hour, ":MM". None: only for every: minutes.
        days: None          # [None, weekdays, month day]; For day or week: the weekdays (mon … sun); for month: a day of the month, 1 to 28. None: every day (day), Monday (week), the 1st (month).
    freshness:
        stale_after_hours: auto          # [auto, positive float]; Data age, hours, after which the HTML page shows the stale banner. auto: one cadence period plus 25%.
        stamp: true          # [true, false]; Draw the "data as of" stamp, with the cadence, in every output.
    status:
        file: auto          # [auto, text]; The status file. auto: <name>.status.json in output_folder, or beside this file if output_folder is None.
    on_failure:
        command: None          # [None, list of text]; Program and arguments run when a run fails, not through a shell. Gets FORGEGRAPH_JOB, FORGEGRAPH_STATUS_FILE and FORGEGRAPH_ERROR. None: none.
        timeout_seconds: 60          # [positive int]; Time allowed for the command before it is stopped.
```

Kept out of v1 on purpose:

- time zones;
- cron or RRULE strings;
- retries;
- `on_success`;
- per-target cadences;
- data-column freshness;
- logged-off runs;
- environment-variable overrides. Install computes the environment; a user-set option can come if needed.

### 6.2 CLI behaviour

**`forgegraph job install lab.schedule.yaml [--force]`**

1. Validate the schedule and every target, as drawing does today: every file it uses, errors naming the parameter, `--json` problems.
2. Pick the backend:
   - macOS: launchd (`~/Library/LaunchAgents/<label>.plist`, `launchctl bootstrap gui/<uid>`);
   - Linux: a systemd user `.service` plus `.timer` with `Persistent=true` (fallback: cron with a marked block);
   - Windows: Task Scheduler `\ForgeGraph\<name>`, with `StartWhenAvailable=true`, `DisallowStartIfOnBatteries=false`, `StopIfGoingOnBatteries=false`, `ExecutionTimeLimit=PT1H`, `InteractiveToken`.
3. The entry runs `<absolute sys.executable> -m forgegraph job run <absolute schedule path>`. With the interpreter given by absolute path, PATH stops mattering. The environment is explicit: `HOME`, `LANG`/`LC_ALL`, `MPLBACKEND=Agg`, and `PATH` set to a minimal known value. The status file records it.
4. Proof run through the real scheduler, waiting for the status file's `last_attempt` to change (timeout around 2 min; around 70 s more for cron):
   - `launchctl kickstart gui/<uid>/<label>`;
   - `systemctl --user start …service`;
   - `schtasks /run /tn …`;
   - cron: a one-off line for the next minute.
5. Report the result. If the proof run fails, see Q4.

Installing a name that already exists with a different definition needs `--force`, the same rule as `skill install`.

**`forgegraph job list [--json]`** lists only ForgeGraph's entries:

- found by label prefix, unit-name prefix, the `\ForgeGraph\` folder, or the crontab block markers;
- for each: name, backend, cadence, schedule file, next run where the backend gives it, and the last result and data age from the status file;
- an entry whose schedule file is missing is listed as broken.

**`forgegraph job remove <name> [--json]`** unregisters the entry and deletes the scheduler files (bootout, `disable --now` plus `daemon-reload`, `schtasks /delete /f`, or block removal). It leaves outputs, the status file and logs in place.

**`forgegraph job run <schedule>`** is the entry point the scheduler calls, needed but not named in the plan (Q3). It:

1. takes the lock;
2. renders every target (one failing doesn't stop the others);
3. writes the status file atomically;
4. runs `on_failure` if anything failed;
5. exits non-zero on any failure.

---

## 7. Open questions only the owner can decide

1. **A file or flags?** D12 says no separate job format; the build plan says a schedule spec. Recommended: the file, so the job can be reviewed, kept in version control, and read back by `list`. D12 would then be updated.
2. **Linux backend:** systemd user timers first, with cron as fallback (recommended: catch-up, a real proof run, the journal), or cron as the plan says?
3. **Is `job run` a public command?** It's the scheduler's entry point. Users and the GHA recipe could call it too.
4. **Failed proof run on install:** roll back (install either leaves a working job or nothing; recommended, in line with "error, don't fall back") or keep the entry and report?
5. **Logged-out runs:** v1 runs only while the user is logged in on every OS (LaunchAgent, user timer without linger, InteractiveToken). Is that enough, or should there be opt-ins (S4U/Password on Windows, `enable-linger` on Linux)?
6. **What "data as of" means:**
   - the Parquet mtime only (the plan), or also an optional timestamp column (dbt's `loaded_at_field`)?
   - for layouts, the oldest tile's time (recommended) or a stamp per tile?
7. **Stale threshold default:** one period plus 25%, or another rule? Should staleness also fire `on_failure`, or a separate `on_stale`? dbt treats warn and error separately.
8. **Partial failure:** with several targets, render the rest and exit non-zero (recommended), or stop at the first error?
9. **Cadence forms:** is the restricted set in §2 enough, or is a cron-string escape hatch wanted? That would bring in a parser (python-crontab or croniter) and lose exact mapping to Task Scheduler.
10. **Success pings:** add `on_success` in v1, so users can wire up healthchecks/Cronitor dead-man checks? `on_failure` can't detect a job that never runs; only the stale banner does.
11. **Stamp text and placement:** wording, corner, and whether it's a format parameter (journal formats might not want it), given the stamp is meant to appear on every scheduled output.
12. **CI scope:** `systemctl --user` may not have a user bus on hosted Linux runners, so CI may need to test cron, or start a user manager.
