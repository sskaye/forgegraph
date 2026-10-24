# Skill eval results, phase 5

The 44 cases in [skill-evals.md](skill-evals.md) and [the phase 4 set](../phase-04/skill-evals.md), run once each on Opus, Sonnet and Haiku with the reviewed skill: 132 runs, each a fresh Claude Code session in a folder holding only the case's data, the installed skill and ForgeGraph. Opus and Sonnet decide changes; Haiku is reported. I looked at every graph and read every question's answer; what the scripts can't judge is in the comments, one problem each, with a proposal.

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–20 (phase 4) | 19 of 20 | 17 of 20 | 17 of 20 |
| 21–38 (bars, ticks, layers) | 13 of 18 | 15 of 18 | 10 of 18 |
| 39–44 (questions) | 6 of 6 | 6 of 6 | 6 of 6 |
| All | 38 of 44 | 38 of 44 | 33 of 44 |

## After review

Round 1 graded again with the reviewed checks (case 1 takes "A vs. B" either way, case 24 the grade on either axis, cases 26 and 38 relabelled columns, cases 9, 29 and 34 dose 0 left to ForgeGraph, case 16's third turn without looking), the four reference line cases (29–31, 38) run again on all three models with labels placed clear of the data and the "Mean: 14.9" label, and case 24 run again with keys allowed outside the plot area.

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–20 (phase 4) | 19 of 20 | 19 of 20 | 19 of 20 |
| 21–38 (bars, ticks, layers) | 17 of 18 | 18 of 18 | 12 of 18 |
| 39–44 (questions) | 6 of 6 | 6 of 6 | 6 of 6 |
| All | 42 of 44 | 43 of 44 | 37 of 44 |

What still fails:

- **Opus:**
  - case 17: didn't look after its last change;
  - case 30: typed "Mean: 14.86" as the label's text instead of aggregation_value.
- **Sonnet:** case 15, didn't look after its last change.
- **Haiku (reported only):**
  - case 17: created a theme;
  - case 26: its own role column, not the benchmark;
  - case 30: the mean in a note;
  - cases 35 and 36: computed its own CI and SE columns;
  - cases 27, 32 and 36: didn't look.

In the rerun, every reference line label is clear of the data, and the per-group lines in case 31 used "Max: 205". Sonnet's case 30 label reads "Mean: 14.8639": with no tick label format set, the value is written with up to six significant digits. In case 24's rerun, all three models put the key outside the plot area (Opus and Sonnet to its right, with narrower bars to fit; Haiku above it), and none stretched the percent axis. Graphs: [reference line cases, rerun](skill-eval-graphs/round-1/reference-lines-rerun.jpg), [case 24, rerun](skill-eval-graphs/round-1/case-24-key-outside.jpg).

## Round 1

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1. Iris scatter | pass | x and y swapped | x and y swapped |
| 2–14 | pass | pass | pass |
| 15. Passengers, wide | pass | didn't look after its last change | pass |
| 16. Tips, three turns | pass | didn't look after the third turn | didn't look after the third turn |
| 17. A fixed theme parameter | didn't look after its last change | pass (x and y swapped, not checked) | created a theme (x and y swapped) |
| 18. A theme asked for | pass | pass | pass |
| 19. A box plot | pass (drew a stand-in from markers and error bars) | pass | pass |
| 20. Point size by population | pass | pass | pass |
| 21. Mean tip by day | pass (a key for one series) | pass | pass (a key for one series) |
| 22. Penguins by island | pass (zero bars) | pass (zero bars) | pass (zero bars) |
| 23. Tips stacked by meal | pass | pass | pass |
| 24. Diamond cuts by color grade | horizontal, so the column check missed; percent axis to 175 % for the key | pass (percent axis to 220 %) | didn't look (percent axis to 250 %) |
| 25. Life expectancy in the Americas | pass | pass | pass (a key for one series) |
| 26. A reference compound | renamed the benchmark "Compound A (reference)" | pass | its own role column, not the benchmark |
| 27. Passengers with yearly ticks | pass | pass | didn't look (a name for one series) |
| 28. Unemployment with separators | pass | pass | pass (a name for one series) |
| 29. A 50 % line | dose 0 left to the lint | dose 0 left to the lint | dose 0 left to the lint; the label crosses a line |
| 30. Savings rate and its mean | label typed as text; label under the data | label typed as text (a name for one series) | line at a typed number; label under the data |
| 31. Each group's maximum rate | pass (label into the frame) | log x unasked; didn't look | pass (label into the frame) |
| 32. A corner note | pass (a name for one series) | pass (a name for one series) | didn't look (a name for one series) |
| 33. A source line | pass (x and y swapped, not checked) | pass (swapped) | pass (swapped) |
| 34. Replicates, mean ± SD | pass | pass | pass |
| 35. fMRI with confidence intervals | pass | pass | computed its own CI column |
| 36. Bill by party size, ± SE | pass | pass | computed its own SE column; didn't look (a key for one series) |
| 37. SDs from a column | pass | pass | pass |
| 38. Body mass with the overall mean | y column renamed, so the check missed | pass (a key for one series) | pass |
| 39–44. Questions | pass | pass | pass |

Graphs, Opus, Sonnet and Haiku side by side: [cases 1–4](skill-eval-graphs/round-1/cases-1-4.jpg), [5–8](skill-eval-graphs/round-1/cases-5-8.jpg), [9–12](skill-eval-graphs/round-1/cases-9-12.jpg), [13–16](skill-eval-graphs/round-1/cases-13-16.jpg), [17–20](skill-eval-graphs/round-1/cases-17-20.jpg), [21–24](skill-eval-graphs/round-1/cases-21-24.jpg), [25–28](skill-eval-graphs/round-1/cases-25-28.jpg), [29–32](skill-eval-graphs/round-1/cases-29-32.jpg), [33–36](skill-eval-graphs/round-1/cases-33-36.jpg), [37–38](skill-eval-graphs/round-1/cases-37-38.jpg).

The questions' answers all came from `forgegraph catalog` and `forgegraph schema`, and each said what's fixed and what a GraphSpec can change. One slip: Sonnet's error-bar answer suggests checking a "bars" graph type, which doesn't exist.

