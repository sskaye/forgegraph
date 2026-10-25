# Phase 8 deliverable: a dashboard updating daily for a week

The plan's deliverable is a real dashboard, built from your data, updated on a schedule for a week while phase 9 is built. You check it a couple of times; at the end, I read its status file and log and report on its runs.

## Try it first with the sample dashboard

`lab_dashboard.schedule.yaml` renders the phase 7 lab dashboard every weekday at 06:00 into `~/Dashboards`, and shows a macOS notification if a run fails.

Ask the agent to schedule it, e.g. "Schedule review/phase-08/deliverable/lab_dashboard.schedule.yaml on this Mac." It will schedule `forgegraph job run review/phase-08/deliverable/lab_dashboard.schedule.yaml` by the method of its choice. Then:

- `~/Dashboards/lab_throughput.html` is the page, with the "data as of" footnote under each tab, and a banner once the data is older than its weekday schedule allows (90 hours);
- `~/Dashboards/lab_dashboard.status.json` and `lab_dashboard.log` record every run;
- `forgegraph job run review/phase-08/deliverable/lab_dashboard.schedule.yaml` runs it once by hand.

## Then with your data

1. Copy the phase 7 dashboard folder somewhere outside the repository, put your export beside it, and ask the agent to adapt the preparation and GraphSpecs to it (as the phase 7 README says).
2. Copy `lab_dashboard.schedule.yaml` beside it, and set `targets.files` to your layout, `output_folder` to where you want the page, and `cadence` to daily (`interval_unit: day`, `at: "06:00"`) or weekdays.
3. Ask the agent to schedule it.

The job only renders. Keeping the Parquet files current is up to your data's own pipeline: if your export lands somewhere each day, its preparation script has to run before 06:00 (for example as its own scheduled task). The footnote and the banner show when that didn't happen.

When the week is up, tell me where the schedule file is and I'll report on its runs.
