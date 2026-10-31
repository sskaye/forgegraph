# Schedules

A **schedule** re-renders GraphSpecs and layouts on a cadence, so a dashboard keeps up with its data. It's a file, `*.schedule.yaml`, so it can be reviewed and kept in version control like any other spec. The [schedule specification](../reference/specifications/schedule.md) lists every parameter.

## A schedule file

This one, from the agent skill's examples, renders a layout every weekday at 06:00:

```yaml
--8<-- "src/forgegraph/skill/forgegraph/examples/figure.schedule.yaml"
```

- **targets.files** are the GraphSpec and layout files rendered on each run, as paths from the schedule's folder. `targets.output_folder` saves their outputs elsewhere; by default, each is saved beside its file.
- **cadence.interval** is a count of one unit: minute, hour, day, week, month or year. For minutes, hours and months, the count must divide 60, 24 or 12; for the other units, it must be 1. So every cadence runs at exactly the same times on every scheduler.
- **cadence.at** says when in each unit the job runs: `":30"`, `"06:00"`, `"mon 06:00"`, `"1 06:00"` (the first of the month) or `"Jan 1 06:00"`, or a list of these, as above. Times are the machine's local time.
- **on_failure.command** and **on_success.command** are programs, with their arguments, run without a shell when a run fails or succeeds, such as an alert. on_success lets a check-in service notice a job that has stopped running, which on_failure can't.

A schedule usually extends the built-in pack's `schedule`, or a pack's own, such as the example acme pack's `workday`, which sets the cadence and the failure alert for its users.

## Running it

```bash
forgegraph job run figure.schedule.yaml
```

`job run` runs the schedule once: it renders every target, writes the status file, and runs on_failure or on_success. A target that fails is recorded, and the others still render; the command exits with 1 if any failed.

ForgeGraph doesn't schedule the command itself. Whatever schedules commands where you work runs it at the schedule's times: cron, launchd, systemd, Task Scheduler, a GitHub Actions workflow, or an agent's scheduled task. For the schedule above, a cron line is:

```text
0 6 * * 1-5 forgegraph job run /path/to/figure.schedule.yaml
```

Each run renders the data files as they are; keeping them current is up to you. On macOS, a background job that writes into a cloud-synced folder needs Full Disk Access.

## Knowing the data is fresh

- **The stamp.** Every output shows a "data as of" footnote in the image itself, with the cadence in words. Its time is the oldest data file's, so the same data gives the same image, and one stale tile makes a layout stale. `freshness.stamp.show` turns it off.
- **The stale banner.** An HTML page shows a banner when its data is older than `freshness.stale_after_hours`, by default the time between runs plus 25 %, so a job that stopped can't look current. It works where the page's scripts run; the footnote is what always shows.
- **The status file.** Every run writes it whole, by default `<name>.status.json` in the output folder, or beside the schedule: the last attempt and the last success, the failures in a row, and for each target its outputs, rows, data files and their times, lint and errors. `job run` also writes a log.

Stale data isn't a failed run: a run that succeeds on old data shows it in the stamp, the banner and the status file, not through on_failure.
