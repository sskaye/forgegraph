# Skill eval results, phase 8

The 57 cases in [skill-evals.md](skill-evals.md), [the phase 5 set](../phase-05/skill-evals.md) and [the phase 4 set](../phase-04/skill-evals.md), run once each on Opus, Sonnet and Haiku with the updated skill: 171 runs, each a fresh Claude Code session in a folder holding only the case's data, the installed skill and ForgeGraph. Opus and Sonnet decide changes; Haiku is reported. I looked at every graph and read every reply; what the scripts can't judge is in the comments, one problem each, with a proposal. The proposals that change a spec are comments on its page: [layout](../../docs/specs/layout/default.md) (two), [schedule](../../docs/specs/schedule/default.md) (one) and [xy graph type](../../docs/specs/graph_type/xy.md) (two).

No job was installed. Haiku ran `forgegraph job install` once without asking (case 53); the stand-in `launchctl` refused it and ForgeGraph removed the file it had written.

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–20 (phase 4) | 20 of 20 | 19 of 20 | 18 of 20 |
| 21–38 (bars, ticks, layers) | 16 of 18 | 17 of 18 | 13 of 18 |
| 39–44 (questions) | 5 of 6 | 6 of 6 | 6 of 6 |
| 45–50 (layouts) | 2 of 6 | 5 of 6 | 2 of 6 |
| 51–52 (date axes) | 2 of 2 | 0 of 2 | 2 of 2 |
| 53–55 (scheduled jobs) | 3 of 3 | 1 of 3 | 1 of 3 |
| 56–57 (questions) | 2 of 2 | 1 of 2 | 2 of 2 |
| All | 50 of 57 | 49 of 57 | 44 of 57 |

What fails, by cause:

- **Layouts at the default format are too small** (cases 46–48): Opus's 2×2 grid couldn't be drawn; Sonnet's dashboard couldn't, so it built its own HTML page. Every three-panel figure that drew has small panels.
- **A layout can't save HTML** without a format of its own (case 48, Opus).
- **Eval cases:** the cell durability data's gap is deliberate (45–46); case 57 doesn't say ForgeGraph (Sonnet); case 44's answer said "locks" (Opus).
- **The image check:** of five misses on Opus and Sonnet, four rendered nothing new after looking.
- **Scheduling:** Sonnet scheduled case 54 as a task in its own session, to rebuild the Parquet file before each render.
- **Haiku (reported only):**
  - cases 47–49: no layout, or one too small to draw;
  - case 26: its own role column, not the benchmark;
  - case 35: computed its own CI column;
  - case 17: created a theme;
  - cases 11, 27 and 53: didn't look;
  - case 33: a test image made outside ForgeGraph;
  - case 54: downloaded other data and scheduled a session task.

## Round 1

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 3. Penguins by shape | pass | didn't look after its last change (axis titles) | pass |
| 11. Geyser with limits | pass | pass | didn't look |
| 17. A fixed theme parameter | pass | pass | created a theme |
| 25. Life expectancy in the Americas | pass | pass | didn't look (every other country named) |
| 26. A reference compound | pass | a test/reference color column, not the benchmark | the same |
| 27. Passengers with yearly ticks | pass | pass | didn't look (a name for one series) |
| 29. A 50 % line | "didn't look": its renders after looking were of copies in its scratchpad | pass | pass |
| 33. A source line | pass | pass | a test image made outside ForgeGraph |
| 35. fMRI with confidence intervals | "didn't look": the render after looking was `forgegraph render --help` | pass | computed its own CI column |
| 44. Palette and font question | said "locks", not "fixed" or "locked" | pass | pass |
| 45. Two panels | the data's gap left to the lint (a key under each panel) | pass | pass |
| 46. Three panels, one spanning | the data's gap left to the lint; small panels | pass (small panels; one tile's key below the figure) | the data's gap left to the lint |
| 47. A blank cell | too small for any labelling: no image | pass (small panels, a key on each) | too small; drew two separate graphs instead |
| 48. A dashboard page | a PNG, not HTML: the layout can't set file types | too small; built its own HTML page around separate graphs | no layout |
| 49. A dashboard with tabs | pass | pass | no layout |
| 50. Widths, as a follow-up | pass | pass | pass (a name for one series) |
| 51. Weekly bars | pass (labels every third week, "%d %b") | weeks written as text ("06 Jul") | pass ("%b %d") |
| 52. A weekly tick step | pass (first tick Dec 31; "%b %d") | "didn't look": re-rendered after reverting a try (first tick 31 Dec; "%d %b") | pass |
| 53. Every weekday | pass | "didn't look": the render after looking was its `job run` | didn't look; installed without asking (refused) |
| 54. Every two hours | pass (suggests a crontab line that rebuilds the Parquet file first) | a task in its own session, no schedule file | the same, with data it downloaded |
| 55. Monthly, run once | pass | pass | pass |
| 56. Several graphs in one figure | pass | pass | pass |
| 57. Re-rendering every morning | pass | answered about Claude's own scheduling tools | pass |
| Every other case | pass | pass | pass |

Graphs, Opus, Sonnet and Haiku side by side: [cases 1–4](skill-eval-graphs/cases-1-4.jpg), [5–8](skill-eval-graphs/cases-5-8.jpg), [9–12](skill-eval-graphs/cases-9-12.jpg), [13–16](skill-eval-graphs/cases-13-16.jpg), [17–20](skill-eval-graphs/cases-17-20.jpg), [21–24](skill-eval-graphs/cases-21-24.jpg), [25–28](skill-eval-graphs/cases-25-28.jpg), [29–32](skill-eval-graphs/cases-29-32.jpg), [33–36](skill-eval-graphs/cases-33-36.jpg), [37, 38, 45 and 46](skill-eval-graphs/cases-37-38-45-46.jpg), [47–50](skill-eval-graphs/cases-47-50.jpg), [51–54](skill-eval-graphs/cases-51-54.jpg), [55](skill-eval-graphs/cases-55.jpg). The failed layouts, drawn again at 300 mm: [layouts at 300 mm](skill-eval-graphs/layouts-at-300-mm.jpg).

The date axes drew as designed wherever the agents left the labels to ForgeGraph (the lab dashboards, case 49). Every agent that set a weekly step also set its own label format, which gave zero-padded days and no year. Every Opus and Sonnet scheduling reply said the job can't pick up changes to the CSV, since it only renders the Parquet file.

