# Skill eval results, phases 6 and 9

The 62 cases in [skill-evals.md](skill-evals.md) and the earlier sets ([phase 8](../phase-08/skill-evals.md), [phase 5](../phase-05/skill-evals.md), [phase 4](../phase-04/skill-evals.md)), run once each on Opus, Sonnet and Haiku: 186 runs a round. The earlier cases' requests are now in full sentences. Each run is a fresh Claude Code session in a folder holding only the case's data, its packs and folder config, the installed skill and ForgeGraph, with a main config of its own. Opus and Sonnet decide changes; Haiku is reported. I looked at every graph, and read the reply of every failure and of every pass the graphs made me doubt.

| Round | Opus | Sonnet | Haiku | All |
| --- | --- | --- | --- | --- |
| 1 | 58 of 62 | 57 of 62 | 49 of 62 | 164 of 186 |
| 2 | 61 of 62 | 56 of 62 | 50 of 62 | 167 of 186 |

**Between rounds 1 and 2:**
- **The skill:** draw on the blank canvas only if the user asks once told; dashboards and multi-panel graphs named in the description; "Don't use other graphing libraries, or write charts by hand."
- **ForgeGraph:** when bars don't fit and the theme leaves their width variable, the error names `series.bar.width` in the GraphSpec.
- **The cases:** case 26 accepts a role column as well as the benchmark.

## Round 2

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–20 (phase 4) | 19 of 20 | 20 of 20 | 20 of 20 |
| 21–38 (bars, ticks, layers) | 18 of 18 | 17 of 18 | 12 of 18 |
| 39–44 (questions) | 6 of 6 | 6 of 6 | 6 of 6 |
| 45–50 (layouts) | 6 of 6 | 3 of 6 | 3 of 6 |
| 51–52 (date axes) | 2 of 2 | 0 of 2 | 0 of 2 |
| 53–55 (scheduled jobs) | 3 of 3 | 3 of 3 | 2 of 3 |
| 56–57 (questions) | 2 of 2 | 2 of 2 | 2 of 2 |
| 58–62 (packs, configs, the blank canvas) | 5 of 5 | 5 of 5 | 5 of 5 |
| All | 61 of 62 | 56 of 62 | 50 of 62 |

Haiku's case 48 counts as a pass: its dashboard is ForgeGraph's own HTML page, and the check counted only image files. The check now counts a page too.

What the changes did:
- **Drawing anyway:** no agent drew on the blank canvas unasked. The serif font was a standard graph on every model (17), every model asked about the box plot instead of drawing it (19), and Sonnet drew the horizontal bars with ForgeGraph (25).
- **Dashboards:** Sonnet built both dashboards as ForgeGraph layouts (48, 49), and so did Haiku in case 48. Haiku still built its own HTML page for the tabbed dashboard (49).
- **Weekly bars:** Opus now plots the weeks as dates, with narrower bars (51). Sonnet narrowed its bars but wrote the weeks as text, and Haiku wrote them as "W28".

What still fails:
- **The image check:** Opus (15), Sonnet (29, 47, 48, 49) and Haiku (25, 29, 30, 45, 52) rendered again after their last look, as in every round so far.
- **A weekly tick step** (52, Sonnet): to avoid a first tick labelled Dec 31, it plotted days since Jan 1 as numbers instead of dates.
- **Haiku (reported only):**
  - case 21: its own tick labels, with each day's count;
  - case 30: a mean line without its value as the label;
  - case 33: no source line;
  - case 35: computed its own confidence-interval column;
  - case 49: built its own HTML page;
  - case 51: weeks as text;
  - case 55: wrote a LaunchAgent for the monthly schedule without being asked. The eval's stand-in refused to load it, and the runner removed it;
  - case 59: drew with acme's theme in place of the base theme, and said so only afterwards.

### Results

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 15. Passengers as a monthly series | didn't look after its last render | pass | pass |
| 21. Bars of the average tip | pass | pass | its own tick labels |
| 25. Life expectancy in the Americas | pass | pass | didn't look |
| 29. A 50 % line | pass | didn't look | didn't look |
| 30. The savings rate's mean | pass | pass | no value label; didn't look |
| 33. A source line | pass | pass | no source line |
| 35. fMRI with confidence intervals | pass | pass | its own CI column |
| 45. Two panels | pass | pass | didn't look |
| 47. A blank cell | pass | didn't look | pass |
| 48. A dashboard page | pass | didn't look | pass (a ForgeGraph HTML page) |
| 49. A dashboard with tabs | pass | didn't look | its own HTML page |
| 50. Widths, as a follow-up | pass | pass | the check found no render to look after |
| 51. Weekly bars | pass | weeks as text | weeks as text |
| 52. A weekly tick step | pass | days since Jan 1, not dates | didn't look |
| 55. Monthly, run once | pass | pass | wrote a LaunchAgent unasked (removed) |
| 59. A pack the config doesn't allow | pass | pass | pass, but drew with acme's theme, said afterwards |
| Every other case | pass | pass | pass |

Graphs, Opus, Sonnet and Haiku side by side, with each run's grade: [cases 1–4](skill-eval-graphs/round-2/cases-1-4.jpg), [5–8](skill-eval-graphs/round-2/cases-5-8.jpg), [9–12](skill-eval-graphs/round-2/cases-9-12.jpg), [13–16](skill-eval-graphs/round-2/cases-13-16.jpg), [17–20](skill-eval-graphs/round-2/cases-17-20.jpg), [21–24](skill-eval-graphs/round-2/cases-21-24.jpg), [25–28](skill-eval-graphs/round-2/cases-25-28.jpg), [29–32](skill-eval-graphs/round-2/cases-29-32.jpg), [33–36](skill-eval-graphs/round-2/cases-33-36.jpg), [37–40](skill-eval-graphs/round-2/cases-37-40.jpg), [41–44](skill-eval-graphs/round-2/cases-41-44.jpg), [45–48](skill-eval-graphs/round-2/cases-45-48.jpg), [49–52](skill-eval-graphs/round-2/cases-49-52.jpg), [53–56](skill-eval-graphs/round-2/cases-53-56.jpg), [57–60](skill-eval-graphs/round-2/cases-57-60.jpg), [61–62](skill-eval-graphs/round-2/cases-61-62.jpg).

## Round 1

**Grading.** The first grading gave 155 of 186. Three checks were wrong after phase 6, and the runs were graded again from their folders, without running the agents again:

1. Case 18: a theme in a pack is named pack/big_labels, which the check didn't accept.
2. Case 58: the check took the agents' GraphSpec, which extends acme's, for a new theme, and took the pack's own example for the agents' GraphSpec.
3. Case 55: an agent that redraws by running the schedule (`forgegraph job run`) wasn't counted as drawing, so its looking at the image wasn't either.

Case 61 ran under the pack's earlier name, boxed_sans, and keeps its first grading. Case 26 counts as a pass on every model: a role column is as good as the benchmark.

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–20 (phase 4) | 20 of 20 | 20 of 20 | 17 of 20 |
| 21–38 (bars, ticks, layers) | 17 of 18 | 17 of 18 | 15 of 18 |
| 39–44 (questions) | 6 of 6 | 6 of 6 | 6 of 6 |
| 45–50 (layouts) | 5 of 6 | 4 of 6 | 3 of 6 |
| 51–52 (date axes) | 1 of 2 | 0 of 2 | 0 of 2 |
| 53–55 (scheduled jobs) | 2 of 3 | 3 of 3 | 3 of 3 |
| 56–57 (questions) | 2 of 2 | 2 of 2 | 1 of 2 |
| 58–62 (packs, configs, the blank canvas) | 5 of 5 | 5 of 5 | 4 of 5 |
| All | 58 of 62 | 57 of 62 | 49 of 62 |

The new cases worked as designed. Every agent drew in acme's house style, by extending acme's own GraphSpec (58). Every agent refused a pack the config doesn't allow, by name (59). Every agent made the lab theme in a pack it listed in forgegraph.toml, and said the graph was non-standard (60). Every agent used the forgegraph_base_2 theme (61), and drew a watermarked violin plot on the blank canvas (62).

What fails, or passes when it shouldn't, by cause:

- **Drawn anyway, unasked** (passes the checks): Sonnet drew a serif font on the blank canvas around the theme's fixed font (17), and a box plot (19). When its GraphSpec's vertical bars didn't fit, it drew horizontal bars in matplotlib, which ForgeGraph can draw (25). Haiku drew a box plot (19). In case 59, Sonnet used acme's theme in place of the base theme the user named, without asking.
- **Dashboards by hand** (48 Sonnet and Haiku, 49 Haiku): Claude Code now gives every session an Artifact tool and a dataviz skill, which claims "ANY chart". These agents built their own HTML pages with charts in them, instead of a ForgeGraph layout.
- **Weekly bars** (51, every model): every agent met "each bar needs 45.0 pt at each place, but places are 24.3 pt apart; narrow the bars in the theme…". The base theme's bars are 2.5 × the base size, too wide for 15 weekly bars at the base format. The message points at the theme, though the GraphSpec can set the width, so each agent wrote its weeks as text.
- **The image check:** Opus (21, 48, 55), Sonnet (47, 52) and Haiku (11, 25, 38, 50, 52) rendered again after their last look, as in phases 4 and 8. You chose to leave this.
- **A reference compound** (26, Sonnet and Haiku): a role column instead of the benchmark, which is fine; the case now accepts either.
- **A theme the user asks for is non-standard** (18 and 60, every model, as designed): the agent's new pack is in forgegraph.toml but not in the main config, so its graphs are watermarked.
- **Haiku (reported only):**
  - case 17: created a theme for a serif font;
  - case 36: computed its own standard-error column;
  - case 19: didn't say ForgeGraph has no box plot;
  - case 57: didn't name `forgegraph job run`;
  - case 60: wrote the palette as hex colors, in its own order.

### Results

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 11. Geyser with limits | pass | pass | didn't look |
| 17. A serif typeface | pass | pass, but drawn on the blank canvas unasked | created a theme |
| 19. A box plot | pass | pass, but drawn on the blank canvas unasked | drawn unasked; didn't say there's no box plot |
| 21. Bars of the average tip | didn't look after its last render | pass | pass |
| 25. Life expectancy in the Americas | pass | its GraphSpec's vertical bars didn't fit, so it drew horizontal bars in matplotlib on the blank canvas | didn't look |
| 26. A reference compound | pass | pass (a role column, not the benchmark) | pass (the same) |
| 36. Mean bill with standard errors | pass | pass | its own standard-error column |
| 38. Body mass with a mean line | pass | pass | didn't look |
| 47. A blank cell | pass | didn't look | pass |
| 48. A dashboard page | didn't look | its own HTML page | its own HTML page |
| 49. A dashboard with tabs | pass | pass | its own HTML page |
| 50. Widths, as a follow-up | pass | pass | didn't look in the first turn |
| 51. Weekly bars | weeks as text, after the bar-width error | the same | the same |
| 52. A weekly tick step | pass | didn't look | didn't look |
| 55. Monthly, run once | didn't look after its last run | pass | pass |
| 57. Re-rendering every morning | pass | pass | didn't name `job run` |
| 59. A pack the config doesn't allow | pass | pass, but used acme's theme in place of the base theme asked for, without asking | pass |
| 60. A theme for the project | pass | pass | the palette as hex colors |
| Every other case | pass | pass | pass |

Graphs, Opus, Sonnet and Haiku side by side, with each run's grade: [cases 1–4](skill-eval-graphs/round-1/cases-1-4.jpg), [5–8](skill-eval-graphs/round-1/cases-5-8.jpg), [9–12](skill-eval-graphs/round-1/cases-9-12.jpg), [13–16](skill-eval-graphs/round-1/cases-13-16.jpg), [17–20](skill-eval-graphs/round-1/cases-17-20.jpg), [21–24](skill-eval-graphs/round-1/cases-21-24.jpg), [25–28](skill-eval-graphs/round-1/cases-25-28.jpg), [29–32](skill-eval-graphs/round-1/cases-29-32.jpg), [33–36](skill-eval-graphs/round-1/cases-33-36.jpg), [37–40](skill-eval-graphs/round-1/cases-37-40.jpg), [41–44](skill-eval-graphs/round-1/cases-41-44.jpg), [45–48](skill-eval-graphs/round-1/cases-45-48.jpg), [49–52](skill-eval-graphs/round-1/cases-49-52.jpg), [53–56](skill-eval-graphs/round-1/cases-53-56.jpg), [57–60](skill-eval-graphs/round-1/cases-57-60.jpg), [61–62](skill-eval-graphs/round-1/cases-61-62.jpg).

