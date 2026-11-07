# Skill eval results, 0.8.0

The 70 cases: the 61 earlier ones and the nine in [skill-evals.md](skill-evals.md), run once each on Opus, Sonnet and Haiku with the skill as it is on this branch, whose examples are now the documentation's. Each run is a fresh Claude Code session in a folder holding only the case's data, the installed skill and ForgeGraph. Opus and Sonnet decide changes; Haiku is reported. I looked at every new case's graph on every model, and read the reply of every failure.

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–62, earlier (61 cases) | 60 of 61 | 52 of 61 | 54 of 61 |
| 63–71, new (9 cases) | 9 of 9 | 8 of 9 | 7 of 9 |
| All | 69 of 70 | 60 of 70 | 61 of 70 |
| Phase 9, round 2 (62 cases) | 61 of 62 | 56 of 62 | 50 of 62 |

The earlier cases are numbered 1 to 62 without 61, a theme from the forgegraph_base_2 pack: that pack went in 0.4.0 (#61), and the case with it. So this round has one earlier case fewer than phase 9.

The same, with not looking after the last render counted as a pass:

| Cases | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1–62, earlier (61 cases) | 61 of 61 | 60 of 61 | 58 of 61 |
| 63–71, new (9 cases) | 9 of 9 | 9 of 9 | 7 of 9 |
| All | 70 of 70 | 69 of 70 | 65 of 70 |
| Phase 9, round 2 (62 cases) | 62 of 62 | 60 of 62 | 55 of 62 |

Without it, the failures are Sonnet's weeks as text (51), and Haiku's swapped axes (3), unasked theme (17) and its own HTML pages (49, 65, 68).

## Checks corrected

Four checks failed answers that were right. I corrected them and graded the same runs again, without running them again:

1. **69, an IQR cap** (every model): capping the axis leaves points out of view, which lint reports as `outside-limits`. The case now allows it.
2. **71, a wrapping title** (Haiku): `title.max_wrap: 5` lets the title wrap, as asked; the check accepted only 1 to 3. It now accepts any wrap.
3. **44, palette and font** (Opus): the reply said the theme "fixes" the palette and fonts; the check looked for "fixed" or "lock". It now takes "fixes" too.
4. **66, a checkbox for each month** (Opus): twelve lines with the theme's fixed palette of seven colors always raise `too-many-groups`. Opus said so, and gave each month its own color and marker together. The case now allows it.

## The new cases

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 63. A dropdown for the y column | pass | didn't look after its last render | pass |
| 64. Radio buttons above the graph | pass | pass | pass |
| 65. Both axes chosen by the reader | pass | pass | wrote its own HTML page |
| 66. A checkbox for each series | pass | pass | pass |
| 67. A line the reader can show | pass | pass | pass |
| 68. Two panels, one dropdown | pass | pass | six ForgeGraph graphs in its own page |
| 69. An axis capped by an IQR rule | pass | pass | pass |
| 70. Geometric statistics | pass | pass | pass |
| 71. A title that wraps | pass | pass | pass |

The graphs:

- **Choice and toggle layers:** Opus and Sonnet used both as intended, from the dropdown to the shared control in a layout. In 66, Opus's key carries the twelve checkboxes; Haiku colored the months along a sequential scale.
- **63:** Opus and Haiku put bill length on x and let the dropdown change it; Sonnet put body mass on x. Both read the request fairly.
- **69:** every model capped the y-axis at `3IQR`. Opus added a note saying how many prices aren't shown, and Sonnet capped the x-axis too.
- **70:** every model used `geom_mean` and `geom_ci`, and labelled the error bars.
- **Haiku, 65 and 68:** in 65 it wrote its own page with two dropdowns. In 68 it said "layouts can't host layers", drew the six combinations with ForgeGraph, and wrote a page around them. Same-named choice layers in a layout's tiles share one control, which the skill doesn't say and the layers guide does.

## What still fails

1. **The image check** (Opus 1, Sonnet 9, Haiku 4): the agent looks at the image, makes a last small edit (often adding a legend setting and then taking it out again), renders, and doesn't look again. It's the same pattern as every earlier round, but Sonnet did it in 9 cases this round against 4 in phase 9.
2. **Weeks as text** (51, Sonnet): the weekly bars' weeks were written as text, as in phase 9.
3. **Haiku (reported only):** its own HTML pages (49, 65, 68); x and y swapped (3); a theme made for a serif font, unasked (17).

Nothing failed because of the new examples: the agents read them (`cat .claude/skills/forgegraph/examples/polarization.yaml` and the like) and used them.

## Proposals

1. **The image check, Sonnet.** One of:
   1. No change. It's the oldest failure in the set, and its rate moves between rounds.
   2. Run Sonnet's nine image-check cases again, two runs each, to see whether the rate holds. If it does, reword step 5 to "Check the image after every render, including the last."

   Recommendation: 2. It costs about 18 runs, and it tells us whether a skill change is needed before making one.
2. **Haiku's own pages.** One of:
   1. No change, as Haiku is reported only, and Opus and Sonnet built every page with ForgeGraph.
   2. Add to the skill that same-named choice and toggle layers in a layout's tiles share their controls.

   Recommendation: 1. Opus and Sonnet found it unaided, and the skill stays short.
3. **The skill change.** With these results, the examples taken from the documentation and the Layers line can merge as they are.

