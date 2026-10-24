# Skill eval results

The 20 cases in [skill-evals.md](skill-evals.md), run once each on Opus, Sonnet and Haiku: 60 runs a round, each a fresh Claude Code session in a folder holding only the case's data, the installed skill and ForgeGraph. I looked at every graph; what the scripts can't judge is in the comments, one problem each, with a proposal.

| Round | Opus | Sonnet | Haiku | All |
| --- | --- | --- | --- | --- |
| 1 | 16 of 20 | 15 of 20 | 16 of 20 | 47 of 60 |
| 2 | 18 of 20 | 18 of 20 | 15 of 20 | 51 of 60 |
| 3 | 20 of 20 | 18 of 20 | 16 of 20 | 54 of 60 |

**Between rounds 1 and 2:**
- **The skill:** the "Don't use other graphing libraries" rule, "Check the image after each iteration" and "not a temporary one".
- **ForgeGraph:** the okabe_ito palette, a variable key marker size, the date offset fix and the layout fix.

**Between rounds 2 and 3:**
- **The skill:** "including follow-up requests" and "or you were started in one".
- **ForgeGraph:** clearer labelling errors, log-axis ticks from published algorithms fitted to their labels, and the tick-rounding fix.

All three rounds are graded with the current cases file and the current ForgeGraph. One round 2 graph that passed then fails now: Opus's diamonds, whose key no longer fits once the new log ticks add labels to its y axis. Opus's round 3 run, made with the new ticks, met that error and got past it.

## Round 3

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1. Iris scatter | pass | x and y swapped | pass |
| 2. CO2 record | pass | pass | pass |
| 3. Penguins, then marker shapes | pass | pass | pass |
| 4. Chick growth by diet | pass | pass | pass |
| 5. fMRI subject traces | pass | pass | pass |
| 6. Stock prices | pass | pass | pass |
| 7. Gapminder, log x | pass | pass | pass |
| 8. Diamonds, dense | pass | pass | didn't look after its last change; markers at the default size |
| 9. Dose-response on a log axis | pass | pass | didn't look after its last change |
| 10. Sea ice with gaps | pass | pass | pass |
| 11. Geyser with fixed limits | pass | pass | pass |
| 12. Weather in Excel | pass | pass | pass |
| 13. Instrument export | pass | pass | pass |
| 14. European sensor log | pass | pass | pass |
| 15. Passengers, wide | pass | didn't look after its last change | pass |
| 16. Tips, three turns | pass | pass | didn't look after the third turn |
| 17. A fixed theme parameter | pass | pass | created a theme |
| 18. A theme asked for | pass | pass | pass |
| 19. A bar chart | pass | pass | pass |
| 20. Point size by population | pass | pass | pass |

Graphs, Opus, Sonnet and Haiku side by side: [cases 1–4](skill-eval-graphs/round-3/cases-1-4.jpg), [5–8](skill-eval-graphs/round-3/cases-5-8.jpg), [9–12](skill-eval-graphs/round-3/cases-9-12.jpg), [13–16](skill-eval-graphs/round-3/cases-13-16.jpg), [17–20](skill-eval-graphs/round-3/cases-17-20.jpg).

## Round 2

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1. Iris scatter | pass | x and y swapped | pass |
| 2. CO2 record | files left in its session scratchpad | pass | pass |
| 3. Penguins, then marker shapes | pass | pass | didn't look after the second turn |
| 4. Chick growth by diet | pass | pass | pass |
| 5. fMRI subject traces | pass | pass | pass |
| 6. Stock prices | pass | pass | pass |
| 7. Gapminder, log x | pass | pass | no graph: gave up after a labelling error |
| 8. Diamonds, dense | key no longer fits (new log ticks) | pass | pass |
| 9. Dose-response on a log axis | pass | pass | pass |
| 10. Sea ice with gaps | pass | pass | pass |
| 11. Geyser with fixed limits | pass | pass | pass |
| 12. Weather in Excel | pass | pass | pass |
| 13. Instrument export | pass | pass | pass |
| 14. European sensor log | pass | pass | x as hours since the start, not dates |
| 15. Passengers, wide | pass | pass | pass |
| 16. Tips, three turns | pass | didn't look after the third turn | didn't look after the third turn |
| 17. A fixed theme parameter | pass | pass | created a theme |
| 18. A theme asked for | pass | pass | pass |
| 19. A bar chart | pass | pass | pass |
| 20. Point size by population | pass | pass | pass |

No run drew a graph without ForgeGraph; in round 1, six did.

Graphs, Opus, Sonnet and Haiku side by side: [cases 1–4](skill-eval-graphs/round-2/cases-1-4.jpg), [5–8](skill-eval-graphs/round-2/cases-5-8.jpg), [9–12](skill-eval-graphs/round-2/cases-9-12.jpg), [13–16](skill-eval-graphs/round-2/cases-13-16.jpg), [17–20](skill-eval-graphs/round-2/cases-17-20.jpg).

## Round 1

| Case | Opus | Sonnet | Haiku |
| --- | --- | --- | --- |
| 1. Iris scatter | pass | x and y swapped | x and y swapped |
| 2. CO2 record | pass | pass | pass |
| 3. Penguins, then marker shapes | pass | pass | pass |
| 4. Chick growth by diet | pass | pass | pass |
| 5. fMRI subject traces | pass | pass | pass |
| 6. Stock prices | pass | pass | pass |
| 7. Gapminder, log x | pass | didn't look at the final image | drew it with matplotlib |
| 8. Diamonds, dense | didn't look at the final image | pass | pass |
| 9. Dose-response on a log axis | files left in its session scratchpad | pass | pass |
| 10. Sea ice with gaps | pass | pass | pass |
| 11. Geyser with fixed limits | pass | pass | pass |
| 12. Weather in Excel | pass | pass | pass |
| 13. Instrument export | pass | pass | pass |
| 14. European sensor log | files left in its session scratchpad | pass | pass |
| 15. Passengers, wide | pass | pass | pass |
| 16. Tips, three turns | pass | didn't look after the second turn | pass |
| 17. A fixed theme parameter | pass | pass | pass |
| 18. A theme asked for | pass | pass | pass |
| 19. A bar chart | drew it with matplotlib | drew it with matplotlib | drew it with matplotlib |
| 20. Point size by population | pass | drew it with matplotlib | drew it with matplotlib |

Graphs: [cases 1–4](skill-eval-graphs/round-1/cases-1-4.jpg), [5–8](skill-eval-graphs/round-1/cases-5-8.jpg), [9–12](skill-eval-graphs/round-1/cases-9-12.jpg), [13–16](skill-eval-graphs/round-1/cases-13-16.jpg), [17–20](skill-eval-graphs/round-1/cases-17-20.jpg).

