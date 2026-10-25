# Codebase audit at 0.2.0: open items

The items that are done are cleared from this page; they're in PRs #4 to #7.

## Decisions

Each has a comment with the issue, the options and my recommendation.

### <!-- fmc:1 -->1. Parameter names (F9)<!-- /fmc:1 -->

Parameter names mix "." and "_" for the same relation, for example grid.line_width beside series.line.width.

### <!-- fmc:2 -->2. How catalog cards are chosen (F10, A17)<!-- /fmc:2 -->

Which parameters get a card, and the value each card shows, are chosen by hand in each catalog file. The forgegraph_base_2 page is drawn with the base theme's line and marker sizes.

### <!-- fmc:3 -->3. decisions.md (G3)<!-- /fmc:3 -->

docs/design/decisions.md is a log kept while building. Most entries record designs that were later replaced, and some contradict the code.

### <!-- fmc:4 -->4. The public history (H1)<!-- /fmc:4 -->

review/ is out of the public tree, but it's still 33 of the public history's 44 MiB, so every clone downloads it.

### <!-- fmc:5 -->5. Merged branches (C11)<!-- /fmc:5 -->

phase-10-release and post-release-fixes are merged but still on GitHub.

### <!-- fmc:6 -->6. Releasing 0.2.1<!-- /fmc:6 -->

PRs #4 to #7 fix bugs users can hit, among them a typer minimum that let `forgegraph --help` crash.

### <!-- fmc:7 -->7. A refactoring pass<!-- /fmc:7 -->

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

<!-- forgemark-comments
- id: 1
  anchor_text: "1. Parameter names (F9)"
  context_before: "Decisions Each has a comment with the issue, the options and my recommendation."
  context_after: "Parameter names mix \".\" and \"\" for the same relation, for example grid.line_widt"
  author: Claude
  timestamp: 2026-10-25T12:16:31Z
  resolved: false
  body: |
    Issue: "." and "_" are used for the same relation. You set the rule: "_" joins words that name one thing (error_bar); "." goes from a thing to its parts and properties (line.width). Renaming breaks every existing spec.
    
    Rules:
    1. "." from a thing to its parts and properties: line.width, marker.edge.width.
    2. "_" joins words that together name one thing: error_bar, color_bar, plot_area, base_size.
    3. An on/off switch is the thing's .show: grid.show, key.frame.show.
    4. No abbreviations: num becomes count.
    
    Renames the rules require:
    1. grid.line_style, grid.line_width: grid.line.style, grid.line.width
    2. plot_area.line_color, plot_area.line_width: plot_area.line.color, plot_area.line.width
    3. layer.error_bar.line_width: layer.error_bar.line.width; layer.error_bar.cap_size: layer.error_bar.cap.width
    4. layer.reference_line.line_style, line_width: layer.reference_line.line.style, line.width
    5. edge_color, edge_width: edge.color, edge.width (series.marker, series.bar, series.benchmark.marker, series.benchmark.bar)
    6. legend.key.frame_width: legend.key.frame.width
    7. legend.key.sample.marker_size: legend.key.sample.marker.size
    8. encoding.line_style, marker_fill, marker_shape: encoding.line.style, encoding.marker.fill, encoding.marker.shape
    9. legend.key.frame (true/false): legend.key.frame.show
    10. freshness.stamp: freshness.stamp.show
    11. separators.line.border: separators.border.show
    12. series.value_label.total: series.value_label.total.show
    13. axis.tick.minor.num: axis.tick.minor.count
    14. cadence.interval, interval_unit: cadence.interval.count, cadence.interval.unit
    
    Kept: legend.key.row_gap, axis.tick.log_algorithm, axis.tick.label.x_rotation, and names such as connect_order and max_wrap, which already follow the rules.
    
    Proposal, one option for encoding.color and encoding.color_type:
    A. encoding.color.column and encoding.color.type, and every encoding as encoding.<channel>.column, matching axis.x.data.column. The Python API's color= stays.
    B. Keep encoding.color and encoding.color_type.
    
    Recommendation: the renames above with A, all at once in 0.3.0, after 0.2.1. Old names get the existing "unknown parameter; did you mean ..." error.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:24:20.513Z"
      body: Agreed.
- id: 2
  anchor_text: "2. How catalog cards are chosen (F10, A17)"
  context_before: "\"\" for the same relation, for example grid.line_width beside series.line.width."
  context_after: "Which parameters get a card, and the value each card shows, are chosen by hand i"
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: catalog files pick by hand which parameters get a card and each card's value (no_card skips one), so what's shown depends on choices made per parameter. Separately, a pack's catalog is drawn with the values its GraphSpecs set, so the forgegraph_base_2 page shows the base theme's line and marker sizes (A17).
    
    Proposal:
    A. A rule. Every variable parameter gets one card, with no no_card. Its value comes from its range: the other boolean; the next word in a list; twice a number, or the range's bound (1 for a default of 0); one fixed color; one fixed text; for a None default, the range's first other option. The card is drawn on the first baseline in the catalog file where it changes the drawing, and a parameter that changes none is a build error. A catalog file then lists only its baselines (lines, bars, horizontal bars, error bars, a reference line, a note, dates, a log axis, a key, a color bar). A pack's catalog draws every baseline with its own theme's and format's values, which fixes A17.
    B. Keep the hand-written catalog files, and fix A17 alone: a pack's catalog draws with its own theme's and format's values.
    
    Recommendation: A. The cost is that rule-picked values are less illustrative than chosen ones, and every catalog image changes once.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:25:29.495Z"
      body: Agreed.
    - author: Claude
      timestamp: 2026-10-25T12:49:04Z
      body: |
        Before building: I classified every variable parameter's range (about 90). The rule covers most, but about 15 have ranges it can't turn into a valid card value:
        1. Columns: axis.x.data.column, axis.y.data.column, the encodings (color, line_style, marker_shape, marker_fill, detail), and a layer's value columns. "Text" doesn't name a column.
        2. Numbers whose default is None: axis min and max, and tick.step. There's no default to double.
        3. Format strings: the tick label formats, value_label.format, and a layer's label.format. Their range is "auto, text", but a fixed sample text isn't a valid format.
        4. Free text: axis titles, key and color bar titles, and a note's text. A fixed sample works here.
        
        Issue: the rule as agreed leaves 1 to 3 undefined.
        
        Proposal:
        A. Derive these from the baseline's data and the axis, by type, never per parameter:
           1. A column parameter gets the first column of the baseline's data, in the data's order, that the baseline doesn't already use and whose type the parameter takes (numbers for an axis; any for an encoding).
           2. A number with a None default gets a value from the axis it belongs to: min, the axis column's median; max, its median too (drawing the lower half); tick.step, a quarter of the drawn range, rounded to one significant figure.
           3. A format gets one fixed format per value type: ".2f" for numbers, "%b %-d" for dates.
           4. Free text gets one fixed sample, "Sample text".
        B. Let a parameter's definition give its own card value when the rule can't. It's one place, but it's a choice made for each of those parameters.
        C. Apply the rule where it works, and keep hand-picked cards in the catalog files for 1 to 3.
        
        Recommendation: A. Everything stays derived from a parameter's range, its axis and the baseline's data, so no card value is chosen by hand. The cost is more rule code in the catalog builder, and cards like "axis.x.min = 41.3" that are less illustrative than chosen ones.
    - author: Steven
      timestamp: "2026-10-25T13:05:21.967Z"
      body: Agreed
    - author: Claude
      timestamp: 2026-10-25T16:04:21Z
      body: |
        Done, in the catalog-rule PR. Building it needed these refinements, all general rather than per parameter:
        1. Each parameter gets an ordered list of candidate values from its range, and its card is the first candidate and baseline that draws and changes the drawing. Numbers try twice, then half (rounded down for whole numbers); words try those after the default; a font tries each bundled family; an auto figure size tries the other size's value; a list tries one-item lists, then itself reversed.
        2. Generic baselines were added where none showed a parameter: horizontal bars, categories drawn with markers (with the categories on x, and on y), and dates. Baselines no card uses are dropped.
        3. The benchmark's column and value, which a validation rule ties together, become None together. The tie is declared once, beside that rule. Both benchmark cards draw the same, since each sets both.
        4. Exempt, since no value changes the drawing: the format's output and provenance parameters, and a graph type's layer.types. So the format panels show no cards.
        5. Every parameter, fixed ones included, gets a card by the same rule. The page shows the variable ones; the perturbation test draws all of them (175 cases, one per parameter).
        6. A17: a theme's or format's catalog draws every baseline with its own values, and so does a pack's whole page.
- id: 3
  anchor_text: "3. decisions.md (G3)"
  context_before: "The forgegraph_base_2 page is drawn with the base theme's line and marker sizes."
  context_after: "docs/design/decisions.md is a log kept while building."
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: most entries record designs that were later replaced. The history is in git and the PRs. What still matters is the reasons behind current decisions.
    
    Proposal:
    A. Move each reason that still applies into architecture.md, beside its decision, then delete decisions.md.
    B. Keep it as a dated log, marking each superseded entry.
    C. Move it to the private repository's review branch.
    
    Recommendation: A. The architecture doc is then the one design record, and nothing in it is out of date.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:26:28.979Z"
      body: "Agreed, but put it in an appendix at the bottom so that it doesn’t interfere with reading the main architecture details."
- id: 4
  anchor_text: "4. The public history (H1)"
  context_before: "t entries record designs that were later replaced, and some contradict the code."
  context_after: "review/ is out of the public tree, but it's still 33 of the public history's 44"
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: removing review/ stops it growing, but clones still download it from the history: 33 of 44 MiB. Only a history rewrite shrinks clones. PyPI is unaffected; anyone who has cloned must clone again.
    
    Proposal:
    A. After PRs #4 to #7 merge, rewrite main without review/, force-push it, and move the v0.1.0 and v0.2.0 tags to the rewritten commits.
    B. Leave the history as it is.
    
    Recommendation: A, after the merges, so the open PRs don't need rebasing. With only a few commits and two tags it's cheapest now, and it gets more expensive with each release.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:26:54.412Z"
      body: Agreed.
- id: 5
  anchor_text: "5. Merged branches (C11)"
  context_before: ", but it's still 33 of the public history's 44 MiB, so every clone downloads it."
  context_after: "phase-10-release and post-release-fixes are merged but still on GitHub."
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: phase-10-release and post-release-fixes are merged into main but still on GitHub.
    
    Proposal:
    A. Delete both, and turn on GitHub's automatic deletion of merged branches.
    B. Delete both only.
    C. Keep them.
    
    Recommendation: A. Nothing is lost; the commits are in main.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:27:02.495Z"
      body: Agreed.
- id: 6
  anchor_text: "6. Releasing 0.2.1"
  context_before: "es (C11) phase-10-release and post-release-fixes are merged but still on GitHub."
  context_after: "PRs #4 to #7 fix bugs users can hit, among them a typer minimum that let forgegr"
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: the merged PRs fix bugs users can hit: the typer minimum (--help could crash), the matplotlib minimum, errors on dates with time zones, error bars on date axes, and missing font licences in the package metadata.
    
    Proposal:
    A. Release 0.2.1 as soon as PRs #4 to #7 merge, following CONTRIBUTING's new release steps, and release the renames (decision 1) later as 0.3.0.
    B. Wait, and release everything with the renames as 0.3.0.
    
    Recommendation: A. The fixes reach users now, and the breaking change gets its own release.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:28:34.477Z"
      body: "C. I’ll let you know when we’re ready for a release. There are no users yet, so there’s no urgency. Might as well keep working until I roll this out to my company and other people I know, which is in a couple days."
- id: 7
  anchor_text: "7. A refactoring pass"
  context_before: "bugs users can hit, among them a typer minimum that let forgegraph --help crash."
  context_after: "This audit found more bugs than refactorings."
  author: Claude
  timestamp: 2026-10-25T12:16:32Z
  resolved: false
  body: |
    Issue: you noted this audit found more bug checks than refactorings. The refactorings done were the ones found (E1 to E9); a pass looking only for structure wasn't made.
    
    Proposal:
    A. After the PRs merge, a pass only for refactoring: modules that do too much, duplication across modules, abstractions that don't earn their place, and simpler designs. Each finding gets a comment with its proposal, for your review before any change, as here.
    B. No further pass; refactor as features touch the code.
    
    Recommendation: A, done before the renames, so the renames land in the simpler code.
  replies:
    - author: Steven
      timestamp: "2026-10-25T12:28:54.961Z"
      body: Agreed.
-->
