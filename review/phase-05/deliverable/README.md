# Phase 5 deliverable: weekly throughput from a lab run log

A fresh Claude Code session, with the installed ForgeGraph skill and nothing else, was given `lab_runs.xlsx` and one request: "lab_runs.xlsx is our LIMS export. Graph our weekly throughput: completed runs per week for each instrument." This folder holds what it made.

| File | What it is |
| --- | --- |
| lab_runs.xlsx | A synthetic LIMS run log (from `scripts/build_sample_data.py`): 936 runs on four instruments over 15 weeks, title rows above the header, "Completed" also typed `completed` and `Completed `, one run still in progress, a total under the data, and an Instruments sheet. HPLC-02 is down for two weeks in August. |
| prep_weekly_throughput.py | The agent's preparation: completed runs (all three spellings), counted per instrument per week (Monday to Sunday, by finish time), weeks with none as 0. |
| weekly_throughput.parquet | The prepared data: one row per instrument and week. |
| weekly_throughput.yaml | The GraphSpec. |
| weekly_throughput.png | The graph. |

The agent counted 834 completed runs and left out 54 aborted, 47 failed and 1 in progress. It plotted HPLC-02's two empty weeks as zeros, so its line doesn't join straight across them, and flagged them as likely downtime to check. It noted two things:

- **Reading the log:** reading .xlsx files needs the openpyxl package, which isn't installed with ForgeGraph, so it installed it in its working folder.
- **Readability:** four crossing lines are busy. ForgeGraph can't yet draw one small panel per instrument, so it named each line directly instead.

## Repeating it with a real log

Ask the agent the same thing in a folder holding your export: it will read the export, prepare the counts and write the GraphSpec. Once a GraphSpec exists, a new export needs only the preparation step and a redraw: run `python prep_weekly_throughput.py <your export>.xlsx weekly_throughput.parquet`, then `forgegraph render weekly_throughput.yaml`. The preparation assumes this log's layout (a Runs sheet, headers on row 4, these column names); for a different export, ask the agent to adapt it.
