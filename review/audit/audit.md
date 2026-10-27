# Codebase audit at 0.2.0: open items

The items that are done are cleared from this page; they're in PRs #4 to #7.

## Decisions

Each has a comment with the issue, the options and my recommendation.

### 1. Parameter names (F9)

Parameter names mix "." and "_" for the same relation, for example grid.line_width beside series.line.width.

### 2. How catalog cards are chosen (F10, A17)

Which parameters get a card, and the value each card shows, are chosen by hand in each catalog file. The forgegraph_base_2 page is drawn with the base theme's line and marker sizes.

### 3. decisions.md (G3)

docs/design/decisions.md is a log kept while building. Most entries record designs that were later replaced, and some contradict the code.

### 4. The public history (H1)

review/ is out of the public tree, but it's still 33 of the public history's 44 MiB, so every clone downloads it.

### 5. Merged branches (C11)

phase-10-release and post-release-fixes are merged but still on GitHub.

### 6. Releasing 0.2.1

PRs #4 to #7 fix bugs users can hit, among them a typer minimum that let `forgegraph --help` crash.

### 7. A refactoring pass

This audit found more bugs than refactorings.

## Deferred until seen in use

None of these has been seen in real use: no eval run, report or issue has hit them.

1. A5: numbers on a date axis are read as day numbers.
2. A8: distinct categories can share a tick label.
3. A9: bars and side-by-side marks run past the plot area and are clipped.
4. A10: a PDF's record can't be read back when its text holds ") /" or ") >>".
5. A11: rows with a missing group value become a series named "nan".
6. A12: quoted "true" or "false" passes as a boolean.
7. A13: files a spec extends are never validated.
8. A14: a GraphSpec can make its format's width and height both auto.
9. A15: theme values a GraphSpec sets skip the theme's checks.
10. A16: two schedule targets with the same file name overwrite each other.
11. B1 to B26: smaller drawing, validation, job-runner, CLI and catalog problems.
12. C2: publishing isn't gated on CI.
13. C3: actions are pinned by tag in the job that can publish.
14. C4: CI hygiene.
15. C5: the sdist's tests need catalog/.
16. C6: numpy and Pillow are imported but not declared.
17. C9: the deny-list scan skips binary files.
18. F7 point 10: series.bar.gap's range of 0 to 2 has no recorded reason.
19. G9: the blank-canvas escape hatch doesn't say how to draw or save.
20. I4: pytest 8.0 runs test_packs' imported `setup` as module setup.
21. With provenance off, a graph changed after rendering is saved without its watermark.

