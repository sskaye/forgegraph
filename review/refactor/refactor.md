# Refactoring proposals

A pass looking only for structure: modules that do too much, the same logic written twice, wrong boundaries, and loose data where a small type would simplify. Every proposal keeps behaviour identical; drawing changes are checked byte-identical, as in the audit's batch 2.

Each finding has a comment with the issue, the proposal (with options where there are real alternatives) and my recommendation. Reply on each; nothing changes until you have.

Order I'd do them in, if you agree: the spec layer (1 to 8), then drawing (9 to 18), then the CLI, catalog and tests (19 to 26), with 19 before the catalog rule and all of them before the renames.

## Specs, graphs, layouts and jobs

### <!-- fmc:1 -->1. spec/documents.py does five jobs<!-- /fmc:1 -->

The registry, resolution, validation, pack permissions and layers are in one 956-line module, which imports spec/layout.py lazily while layout imports it back.

### <!-- fmc:2 -->2. "The specs a document names" is written a dozen times<!-- /fmc:2 -->

That a GraphSpec names a graph type, theme and format, and a layout a format, is re-derived in about twelve places across four modules.

### <!-- fmc:3 -->3. Resolved values come in three shapes<!-- /fmc:3 -->

Resolution returns values with their source, values with whether they're fixed, or plain values, and about twenty call sites index or convert between them.

### <!-- fmc:4 -->4. A loaded document travels as a tuple<!-- /fmc:4 -->

The document, its registry and its folder are passed as three values through about fifteen signatures, and "a relative path is found from the file that sets it" is written three times.

### <!-- fmc:5 -->5. graph.py is also the shared library<!-- /fmc:5 -->

Layouts, the blank canvas and jobs import inspection, saving, provenance, data reading and spec checks from graph.py, and the provenance record is assembled three times.

### <!-- fmc:6 -->6. The end of a render is written twice<!-- /fmc:6 -->

A graph and a layout's tile finish a render with the same steps, line for line, and a tile copies a prepared graph's fields one by one.

### <!-- fmc:7 -->7. The CLI and jobs branch on "is it a layout"<!-- /fmc:7 -->

The same check appears nine times, choosing between two code paths that differ only in small ways.

### <!-- fmc:8 -->8. Small duplicated constants<!-- /fmc:8 -->

The kind-to-folder map, the base pack's name and its folder are each defined more than once.

## Drawing

### <!-- fmc:9 -->9. Helpers in xy.py reach other modules as callbacks<!-- /fmc:9 -->

Layers, marks and the color bar receive general helpers from xy.py as lambdas and extra parameters.

### <!-- fmc:10 -->10. The render passes are driven twice<!-- /fmc:10 -->

A graph and a layout each run the same lay-out, place and label passes, through a five-function protocol each graph type must provide.

### <!-- fmc:11 -->11. The layout settle loop is written twice<!-- /fmc:11 -->

One graph's layout and a layout's grid run the same measure-and-settle algorithm, and figure.py mixes the figure classes with measuring.

### <!-- fmc:12 -->12. A series' stack, shifts and look travel in parallel lists<!-- /fmc:12 -->

Three lists are zipped together at five sites, and whether a series is the benchmark is decided four times.

### <!-- fmc:13 -->13. The four style dimensions are listed in five places<!-- /fmc:13 -->

Color, line style, marker shape and marker fill each appear in five separate lists in xy.py.

### <!-- fmc:14 -->14. xy.draw is one 170-line function<!-- /fmc:14 -->

It stacks, draws marks, draws layers, sets the axes and decorates, in one function sharing all its locals.

### <!-- fmc:15 -->15. axes.py holds three modules<!-- /fmc:15 -->

Axis data types, the whole calendar subsystem and the exception class other modules need are in one 675-line module.

### <!-- fmc:16 -->16. What a label must stay clear of is defined four ways<!-- /fmc:16 -->

Each kind of placed text builds its own list of obstacles.

### <!-- fmc:17 -->17. Orientation is passed as strings<!-- /fmc:17 -->

About 40 conditionals choose between x and y.

### <!-- fmc:18 -->18. A theme font is built the same way at eight sites<!-- /fmc:18 -->

The same three-part expression builds a font from the theme at each.

## CLI, catalog, tests and scripts

### <!-- fmc:19 -->19. The catalog card loop does four jobs<!-- /fmc:19 -->

One function reads the catalog file, draws, builds the table and places the cards, and the perturbation test re-implements the placement.

### <!-- fmc:20 -->20. Tests write spec documents and projects by hand<!-- /fmc:20 -->

About 30 documents are written out with their full header, the same project setup appears six times, and two copies of a document builder exist.

### <!-- fmc:21 -->21. Forgemark's file format is defined in five places<!-- /fmc:21 -->

The comments-block marker, the anchor regex, carrying comments onto a rebuilt page and stripping review markup are each written more than once.

### <!-- fmc:22 -->22. Every CLI command repeats its failure and output code<!-- /fmc:22 -->

Each command catches its errors and prints JSON or text in its own copy of the same few lines.

### <!-- fmc:23 -->23. Baselines and their regression check are drawn separately<!-- /fmc:23 -->

The script that draws the image baselines and the test that compares against them each have their own drawing code.

### <!-- fmc:24 -->24. The skill evals' grade function is 270 lines<!-- /fmc:24 -->

It checks about 25 expectations inline, and draws and resolves the final GraphSpec twice.

### <!-- fmc:25 -->25. test_catalog.py keeps fast tests out of the dev suite<!-- /fmc:25 -->

The whole module is marked slow, though most of its tests draw nothing.

### <!-- fmc:26 -->26. The visual changelog parses card figures with its own regex<!-- /fmc:26 -->

It reads the markup page.py writes, with its own pattern.

## <!-- fmc:27 -->Not a refactoring<!-- /fmc:27 -->

Found in passing, not seen in use, so deferred: direct labels are placed after style keys, and their search doesn't avoid keys, so a direct label could land on a style key.

<!-- forgemark-comments
- id: 1
  anchor_text: "1. spec/documents.py does five jobs"
  context_before: "Specs, graphs, layouts and jobs"
  context_after: "The registry, resolution, validation, pack permissions and layers are in one 956"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: documents.py holds the registry and loading (72-219), resolution (242-366, 686-716), validation and each kind's rules (369-484, 595-683, 719-846), pack permissions (487-592) and the layers collection (849-956). It imports spec/layout.py lazily (462), and layout.py imports it back lazily (91-94, 273) with Registry under TYPE_CHECKING. Layers follow the same pattern as layout's tabs but live apart from them.
    
    Proposal:
    1. spec/registry.py: load_yaml, Registry, builtin, registry_for, load_document. The three helpers that only query the registry (_owner, _unloaded, _allows) become Registry methods.
    2. spec/resolve.py: entries, chain, resolve, setter, folder_of, explain.
    3. spec/layers.py: the layers collection, shaped like spec/layout.py.
    4. spec/access.py: pack permissions and the non-standard note.
    5. spec/validate.py: validate, the per-kind rules and drawing_problems.
    Imports then run one way (registry, then resolve, then layout and layers, then validate), with no lazy imports or TYPE_CHECKING guard.
    
    Options for callers:
    A. Update every import (about 30 in src, 12 test files).
    B. Keep documents.py as a facade re-exporting the new modules.
    
    Recommendation: A. The three tests that monkeypatch documents would need retargeting under B too, so a facade saves less than it seems.
    
    Cost: mostly moved code; about 30 import lines in src.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:13Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 2
  anchor_text: "2. \"The specs a document names\" is written a dozen times"
  context_before: "6-line module, which imports spec/layout.py lazily while layout imports it back."
  context_after: "That a GraphSpec names a graph type, theme and format, and a layout a format, is"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: "a GraphSpec names graph_type, theme and format; a layout names format" is re-derived in OTHER_KINDS, HEADINGS and CHOICE (documents.py:73-79), _specs_named (221), permission_problems (505), packs_used (531), _choices (628), explain (700), drawing_problems (833), layer_problems (908), graph.used (275), graph._named_problems (437), layouts._format_values (328), layouts._check (342) and spec.layout._sizes_problems (275). Two pairs are copies: _format_settable and _settable (documents.py:633-671), and graph._named_problems and the loop in layouts._check, which give identical messages.
    
    Proposal: one table, NAMES = {"graphspec": ("graph_type", "theme", "format"), "layout": ("format",)}, and one named(kind, doc, reg). Every site above reads from it; the two pairs each become one function, and _graph_type_root becomes chain(...)[-1].
    
    Recommendation: do it. A layout that names a theme, or a new named kind, becomes a one-line change, and validation leaves graph.py and layouts.
    
    Cost: about 90 lines; messages unchanged, so no test changes.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:13Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 3
  anchor_text: "3. Resolved values come in three shapes"
  context_before: "and a layout a format, is re-derived in about twelve places across four modules."
  context_after: "Resolution returns values with their source, values with whether they're fixed,"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: resolution returns {path: Resolved}, {path: (value, fixed)} or {path: value}. The tuple shape forces .get(path, (None,))[0] at about 12 sites; conversions to plain values are written 7 times; explain_layout flattens tiles into "tabs.<tab>.tiles.<tile>.<kind>" strings that the CLI parses back (cli/graphs.py:113); and a prepared graph and a tile each keep two views of the same values.
    
    Proposal: one Values type (a dict of Resolved with .value(path), .fixed(path) and .plain()), returned by resolve, and an Explained dataclass (graphspec, layers, graph_type, theme, format). explain_layout returns the layout's Values and {(tab, tile): Explained}; the CLI builds today's dotted display strings, so its output is unchanged. Graph.values stays a plain dict, since it's public and provenance records it.
    
    Recommendation: do it, in the same pass as 1. Explain becomes a typed structure, which Studio will need.
    
    Cost: about 60 lines across 12 files; 5 test lines that index [0].
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:13Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 4
  anchor_text: "4. A loaded document travels as a tuple"
  context_before: "xed, or plain values, and about twenty call sites index or convert between them."
  context_after: "The document, its registry and its folder are passed as three values through abo"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: load_document returns (doc, reg, folder), threaded through about 15 signatures. "A relative path is found from the folder of the file that sets it" is written three times: graph.data_path (458-470), jobs _from and _place (run.py:80-88) and layouts.tile_files (352-378). explain_layout and nonstandard_packs_of re-implement load_document line for line; load_layout is a pass-through; jobs.load builds the cadence again after validation built it, behind an except that can't be reached.
    
    Proposal: a frozen Loaded(kind, doc, reg, folder), returned by load_document, with resolve(), explain(), setter(path) and place(path) (expanduser, absolute, or relative to the setting file's folder). The three path rules, the two loader copies and load_layout go; jobs takes its cadence from validation.
    
    Recommendation: do it. It's also where per-document caching of chains and entries would go, which today are recomputed on every call.
    
    Cost: about 120 lines across graph, layouts, jobs and the CLI.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:13Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 5
  anchor_text: "5. graph.py is also the shared library"
  context_before: "nd \"a relative path is found from the file that sets it\" is written three times."
  context_after: "Layouts, the blank canvas and jobs import inspection, saving, provenance, data r"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: of graph.py's 579 lines, only Graph, prepare, render, xy, graphspec and load are about one graph. Layouts import 11 names from it, canvas 3, and jobs data_path. The provenance record is built three times with the same boilerplate (Graph.record 189-208, Blank.record canvas.py:72-86, Layout.record 200-223).
    
    Proposal:
    1. forgegraph/drawn.py: the Inspected and Saved mixins, pixel_hash and SpecError (graph.py re-exports SpecError for fg.SpecError).
    2. spec/provenance.py: recorded, used, and one record(level, ...) helper, with the fields a full record adds shared by Graph and Tile.
    3. forgegraph/data.py: data_path and reading the data.
    4. The named-spec checks go to spec (finding 2).
    graph.py ends near 300 lines.
    
    Recommendation: do it. One subtlety to keep: Graph.record inspects only after the provenance-off check, Layout.record before it, so the off check stays with each caller.
    
    Cost: about 150 lines moved, 20 imports.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:13Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 6
  anchor_text: "6. The end of a render is written twice"
  context_before: "d spec checks from graph.py, and the provenance record is assembled three times."
  context_after: "A graph and a layout's tile finish a render with the same steps, line for line,"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: graph.py:405-414 and layouts:550-558 end a render with the same steps line for line (non-standard packs, changed, font problems, check, snapshot, fig.graph). check()'s draw-and-collect-font-problems step and the per-plot lint call are also duplicated (graph.py:170-181, layouts:141-154). Tile repeats eight of Prepared's fields and copies them one by one (layouts:537-549).
    
    Proposal: Inspected.seal(fig, font_problems, nonstandard_packs) for the end of a render, one Prepared.plot_issues(ax, drawing) for lint, and a Tile that holds its Prepared rather than copies of its fields.
    
    Recommendation: do it. The snapshot-after-the-one-lint-draw rule is then written once, so the two render paths can't drift.
    
    Cost: about 60 lines, keeping the order check, snapshot, hash.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 7
  anchor_text: "7. The CLI and jobs branch on \"is it a layout\""
  context_before: "me steps, line for line, and a tile copies a prepared graph's fields one by one."
  context_after: "The same check appears nine times, choosing between two code paths that differ o"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: jobs/run.py checks _is_layout five times (207-306) and cli/graphs.py four times (37-93). stem(path) already returns path.stem for a GraphSpec, so several branches reduce to it, and data records and labelling are gathered differently for each type.
    
    Proposal: one draw_file(path, footnote=None) returning a Graph or Layout, and data_records and labelling_by_name on both, so jobs and the CLI call them without branching.
    
    Recommendation: do it. A third drawn type would need no changes there.
    
    Cost: about 40 lines; outputs unchanged.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 8
  anchor_text: "8. Small duplicated constants"
  context_before: "ears nine times, choosing between two code paths that differ only in small ways."
  context_after: "The kind-to-folder map, the base pack's name and its folder are each defined mor"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: the kind-to-folder map exists three times (parameters.KINDS 38, packs.FOLDERS 49, catalog_build/files.py 28); the base pack's name twice (parameters.BASE_PACK, packs.BASE) and its folder twice (parameters.definition_file 334, packs.base_folder 129); top-level categories are computed twice (documents._categories 595, parameters._graphspec_definitions 436).
    
    Proposal: derive the folder maps from KINDS, keep one BASE and one base_folder, and add one parameters.categories(*kinds).
    
    Recommendation: do it, with 1.
    
    Cost: about 20 lines.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#10.
- id: 9
  anchor_text: "9. Helpers in xy.py reach other modules as callbacks"
  context_before: Drawing
  context_after: "Layers, marks and the color bar receive general helpers from xy.py as lambdas an"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: layers.label_lines takes clear, grow and text_of as callbacks (layers.py:254-256), notes_inside a clear lambda (532), error_bars a shifted lambda and xy's Y_VALUE (319-330), marks.value_labels a text_of (420), and colorbar.add a minor_ticks lambda (72, 86). They're built in xy.place and xy.label (719-743) from helpers that only live in xy.py. The long-form column names are split too: ROW is in layers.py, Y_VALUE in xy.py.
    
    Proposal: move _number_text and _tick_decimals into axes.py beside number_format, _line_text into layers.py, and _Between and _minor_ticks into ticks.py with the other locators. Each module then calls labels.box_clear, marks.grow_to_fit, marks.shifted and the rest itself, and Y_VALUE joins ROW in layers.py.
    
    Recommendation: do it. Six callback parameters go, xy.place drops from 30 lines to about 8, and each module's dependencies show in its imports.
    
    Cost: about 100 lines, mostly moved; tests are black-box here.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 10
  anchor_text: "10. The render passes are driven twice"
  context_before: "he color bar receive general helpers from xy.py as lambdas and extra parameters."
  context_after: "A graph and a layout each run the same lay-out, place and label passes, through"
  author: Claude
  timestamp: 2026-10-25T12:59:04Z
  resolved: false
  body: |
    Issue: graph.py:286-298 and 396-399, and layouts:575-604 and 522-527, both drive lay out, place until nothing moves, label, then re-lay out for an outside key and check it. Each graph type must provide five functions (draw, place, unlabel, label, check_outside); unlabel is only ever called just before label, and xy.unlabel finds notes by how layers.py happens to place them.
    
    Proposal: one driver, finish(tiles, lay_out), used by both: a graph passes one tile, a layout all of them. label() clears what it placed first, through labels.unplace and layers.unplace_notes, so unlabel leaves the protocol. check_outside moves out of xy, since nothing in it is xy's.
    
    Recommendation: do it, with 11. A future graph type then provides draw, place and label only.
    
    Cost: about 80 lines, most outside drawing/; one test monkeypatch retargeted.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 11
  anchor_text: "11. The layout settle loop is written twice"
  context_before: "and label passes, through a five-function protocol each graph type must provide."
  context_after: "One graph's layout and a layout's grid run the same measure-and-settle algorithm"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: figure.layout (199-221) and layouts/arrange.py (264-282) run the same algorithm: measure, compute the room each side needs, place, stop when settled, and after PASSES unsettled passes place with the larger of the last two rooms. The room calculation is written twice almost character for character (figure.py:208-214, arrange.py:97-104). figure.py also mixes the figure classes with measuring; colorbar and lint import it only for measuring.
    
    Proposal: drawing/layout.py with the measuring helpers, one room(ax, renderer), and one settle(measure, put, widest) holding the passes and the last-two rule. Each keeps its own put function. figure.py keeps the figure classes, the watermark and new_figure, which layouts then use too.
    
    Options:
    A. Share room and settle; keep both put functions.
    B. Treat one graph as a 1 by 1 grid and delete one graph's put. Simpler still, but the margins are summed in a different order, so positions could differ in the last bit.
    
    Recommendation: A. The arithmetic is untouched, so output stays identical.
    
    Cost: about 120 lines moved, 30 removed; imports in five or six tests.
  replies:
    - author: Steven
      timestamp: "2026-10-25T13:10:01.465Z"
      body: "I can see both arguments. I’d go with whichever is easier to maintain and keep consistent in the long-term. That seems like B, but you’d know better than me."
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#11, as option B: one graph is laid out as a grid of one tile. Positions moved only in the last bit of a float (figure sizes by up to 9e-16 in), so a few anti-aliasing pixels differ on two catalog cards and one image baseline. Nothing visible changed.
- id: 12
  anchor_text: "12. A series' stack, shifts and look travel in parallel lists"
  context_before: "ure-and-settle algorithm, and figure.py mixes the figure classes with measuring."
  context_after: "Three lists are zipped together at five sites, and whether a series is the bench"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: series, stacked and offsets are zipped at xy.py:504 and 525, marks.py:474 and 513, and layers.py:355, and stored twice more in Drawn. Benchmark or not is decided in _series (xy.py:423-434), again in draw (526-566), in marks.widths (153-158) and in marks.bars (341-352). slots and check_room build the same "series at each place" map (marks.py:167, 374).
    
    Proposal: Series carries its stack and shifts, and a frozen Look (line width, marker size, edges, bar width, z-orders) filled once in _series from the series or benchmark theme paths. Drawn loses stacked and offsets; one _present(series) serves slots and check_room.
    
    Recommendation: do it, with 14.
    
    Cost: about 90 lines in xy, marks and layers; no tests use these internals.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 13
  anchor_text: "13. The four style dimensions are listed in five places"
  context_before: "ther at five sites, and whether a series is the benchmark is decided four times."
  context_after: "Color, line style, marker shape and marker fill each appear in five separate lis"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: color, line style, marker shape and marker fill are listed separately in BY_PATHS (xy.py:36), the _Encodings fields (196, 321), _series (441), _group_warnings (461) and _style_keys (862-878). Style keys travel as a loose (handles, names, title, column) tuple.
    
    Proposal: a Dimension(by, encoding_path, theme_path, words, choices) and DIMENSIONS, so each of the five becomes a loop; a StyleKey dataclass replaces the tuple.
    
    Recommendation: do it. A new encoding becomes one row, and the lists can't drift apart. It also makes the renames (decision 1) touch one table instead of five lists.
    
    Cost: about 60 lines in xy.py.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 14
  anchor_text: "14. xy.draw is one 170-line function"
  context_before: "style, marker shape and marker fill each appear in five separate lists in xy.py."
  context_after: "It stacks, draws marks, draws layers, sets the axes and decorates, in one functi"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: draw (xy.py:488-660) stacks and offsets, draws marks, draws layers, sets scales, ticks and limits, decorates, and fills Drawn, sharing all its locals. The last refactor split build_series but not draw.
    
    Proposal: stages, as for build_series: _draw_marks, _axes and _decorate, with draw about 20 lines calling them in order.
    
    Recommendation: do it, after 12, which removes most of its first stage.
    
    Cost: about 170 lines moved, order kept.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:14Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 15
  anchor_text: "15. axes.py holds three modules"
  context_before: "aws layers, sets the axes and decorates, in one function sharing all its locals."
  context_after: "Axis data types, the whole calendar subsystem and the exception class other modu"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: axes.py has axis data types and categories (86-162), the whole calendar subsystem (57-83, 202-378, 415-468), one locator while the others live in ticks.py, the number formatters, and DrawError (53), which marks, layers and layouts import axes.py only for. jobs/run.py imports MONTHS from it.
    
    Proposal: drawing/dates.py for the calendar block (about 250 lines); LogStep to ticks.py; DrawError beside LayoutError in a small errors module.
    
    Recommendation: do it.
    
    Cost: about 300 lines moved, five import sites.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 16
  anchor_text: "16. What a label must stay clear of is defined four ways"
  context_before: "subsystem and the exception class other modules need are in one 675-line module."
  context_after: "Each kind of placed text builds its own list of obstacles."
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: labels.box_clear (328-343), place_interior's own list (201-205), the inside-note test (xy.py:740) and check_outside (xy.py:766-779) each build their own obstacles. The lines_shown flag they pass doesn't mean series lines; it decides whether reference lines and error-bar stems count (labels.py:154).
    
    Proposal: one Obstacles.of(ax, lines=, keys=) with clear(box), built where each caller checks now, keeping each caller's inclusions exactly; the flag gets an honest name.
    
    Recommendation: do it. One place to read or change the clearance rules, which is also where the possible bug below would be fixed if it's ever seen.
    
    Cost: about 70 lines; box_clear kept as a thin wrapper for one test.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 17
  anchor_text: "17. Orientation is passed as strings"
  context_before: "is defined four ways Each kind of placed text builds its own list of obstacles."
  context_after: "About 40 conditionals choose between x and y."
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: base_axis, value_axis, vertical and get/put pairs of ax.get_xlim or get_ylim recur about 40 times across xy, layers and marks.
    
    Proposal: a frozen Along(name) with .other, .lim(ax), .set_lim(ax, lo, hi), .scale(ax) and .xy(base, value), carried in Roles.
    
    Options:
    A. Do it.
    B. Leave it.
    
    Recommendation: B for now. It touches about 120 lines for the smallest gain here, and 12 and 14 remove some of the conditionals anyway. Worth revisiting if a horizontal-first graph type is added.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Not done, as agreed.
- id: 18
  anchor_text: "18. A theme font is built the same way at eight sites"
  context_before: "Orientation is passed as strings About 40 conditionals choose between x and y."
  context_after: "The same three-part expression builds a font from the theme at each."
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: text.font(str(style.theme["font.family"]), style.pt(...), style.weight(...)) is written out at labels.py:183, key.py:57-60, spacing.py:24-36 and figure.py:226 and 312.
    
    Proposal: one Style.font(size_path, weight_path).
    
    Recommendation: do it.
    
    Cost: about 20 lines.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#11.
- id: 19
  anchor_text: "19. The catalog card loop does four jobs"
  context_before: "CLI, catalog, tests and scripts"
  context_after: "One function reads the catalog file, draws, builds the table and places the card"
  author: Claude
  timestamp: 2026-10-25T12:59:05Z
  resolved: false
  body: |
    Issue: build.instance (build.py:181-279) reads the catalog file itself, draws through a closure with an image cache, builds the table rows, and places the cards (numbering baselines, checking each card differs from where it starts). test_perturbation.py:22-48 re-implements the placement and has drifted: it leaves out the layer settings every card draws. A test has to monkeypatch build.read to try one card.
    
    Proposal: catalog_build/cards.py with Drawings (cached drawing, the lenient message image), a pure place(catalog) returning the planned cards, and instance(catalog, ...) taking a Catalog rather than reading one. The perturbation test uses the same place().
    
    Recommendation: do it, before the catalog rule. The rule's "first baseline where the card changes the drawing" then becomes place() trying baselines through Drawings, and the perturbation test can't drift from the build.
    
    Cost: about 150 lines in build.py, a 90-line module, 30 test lines.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 20
  anchor_text: "20. Tests write spec documents and projects by hand"
  context_before: "ble and places the cards, and the perturbation test re-implements the placement."
  context_after: "About 30 documents are written out with their full header, the same project setu"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: about 30 documents are written out with the full header (name, version, description, extends, fixed, variable) across test_jobs, test_layout, test_schedule, test_axes, test_packs and recreations.py, plus YAML strings in five more files. test_specs.child and render_helpers._child are two builders, the second a copy of the package's. "The polarization data and a GraphSpec drawing it" is set up six times; CLI-with-JSON helpers are written three ways.
    
    Proposal: in pack_helpers.py: doc(...), child(kind, parent, values), graphspec_file(folder, ...) and cli(*args) / cli_problems(*args). Convert the dict sites; leave YAML text where the text itself is under test.
    
    Recommendation: do it. A header change becomes one edit instead of 30. It's also most of the work the renames would otherwise do by hand in tests.
    
    Cost: test code only; about 200 lines removed, 50 added.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:15Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 21
  anchor_text: "21. Forgemark's file format is defined in five places"
  context_before: "ame project setup appears six times, and two copies of a document builder exist."
  context_after: "The comments-block marker, the anchor regex, carrying comments onto a rebuilt pa"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: the comments-block marker is defined five times (build.py:31, skill/__init__.py:18, report_skill_evals.py:21, spec_mirror.py:136, mirror_specs.py:20), the anchor regex twice, carrying comments onto a rebuilt page three times, reattaching after a rewrite twice, and stripping review markup twice. build_recreations imports the catalog's write() only to keep its page's comments.
    
    Proposal: one module for the format and the tool: COMMENTS, MARKER, keep(new, old), strip(text) and rewrite(path, text).
    
    Options:
    A. Keep it in catalog_build/.
    B. Move it to forgegraph/forgemark.py, since the CLI, the skill, the catalog and scripts all use it, and the skill importing from catalog_build is the wrong direction.
    
    Recommendation: B.
    
    Cost: about 60 lines across 7 files.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 22
  anchor_text: "22. Every CLI command repeats its failure and output code"
  context_before: "onto a rebuilt page and stripping review markup are each written more than once."
  context_after: "Each command catches its errors and prints JSON or text in its own copy of the s"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: each command repeats "except XError as e: fail(e.problems, as_json); return" (graphs.py, jobs.py, skill.py, catalog.py); the 11 returns exist only because fail is typed as returning (cli/__init__.py:52); helpers take as_json just to call fail; ten commands repeat the JSON-or-text output; and --folder is declared three times.
    
    Proposal: fail(problems) raises, typed NoReturn, and json_errors prints exactly what fail prints today; one report(result, as_json, text); one Folder option beside Json.
    
    Options:
    A. As above: identical output.
    B. Also turn any ProblemsError into problems in json_errors, deleting every try block. Then a pack problem in catalog, pack-notes, schema or explain prints a clean list instead of a traceback in text mode, and a list instead of one joined line in JSON. That's a behaviour change.
    
    Recommendation: A now. B is better behaviour, and matches "messages an agent can act on"; say if you want it.
    
    Cost: about 60 lines in cli/; no test changes.
  replies:
    - author: Steven
      timestamp: "2026-10-25T13:12:14.761Z"
      body: B
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9, as option B: errors that list problems, a pack problem among them, print as problems instead of a traceback.
- id: 23
  anchor_text: "23. Baselines and their regression check are drawn separately"
  context_before: "atches its errors and prints JSON or text in its own copy of the same few lines."
  context_after: "The script that draws the image baselines and the test that compares against the"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: build_recreations.py:45-55 draws the image baselines at 72 dpi without a record, and test_regression.py:23-42 draws what's compared with its own code and its own literal 72. Three more "PNG without a record" helpers exist. LayoutRecreation.render writes a pack.yaml, both configs and two specs by hand, which pack_helpers already does. Two sys.path lines in scripts do nothing.
    
    Proposal: recreations.py gets BASELINE_DPI and one baseline_image() for both kinds, used by the script and the test; LayoutRecreation uses pack_helpers; the dead lines go.
    
    Recommendation: do it. The baseline and its check can't drift apart.
    
    Cost: about 40 lines.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 24
  anchor_text: "24. The skill evals' grade function is 270 lines"
  context_before: "elines and the test that compares against them each have their own drawing code."
  context_after: "It checks about 25 expectations inline, and draws and resolves the final GraphSp"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: run_skill_evals.grade (368-635) handles about 25 expectation keys inline; the final GraphSpec is drawn twice and resolved twice, and its data path computed three times.
    
    Proposal: a Project context built once per grade, with the drawn graph, resolved values and data cached (each keeping its own error, so each check still reports its own), and grade() as a sequence of small check functions in today's order.
    
    Recommendation: do it, checked by regrading a saved run set before and after and comparing the results. That's a regrade of existing transcripts, not a new eval run.
    
    Cost: a dev script reorganised; no tests cover it.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 25
  anchor_text: "25. test_catalog.py keeps fast tests out of the dev suite"
  context_before: "about 25 expectations inline, and draws and resolves the final GraphSpec twice."
  context_after: "The whole module is marked slow, though most of its tests draw nothing."
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: the module-level slow mark (test_catalog.py:27) keeps every test out of uv run pytest, though the catalog-file rules, open_commented, the Forgemark checksum and the committed-page checks draw nothing (reading xy's catalog takes 0.06 s).
    
    Proposal: test_catalog_files.py for the file rules, test_catalog_page.py for the page and Forgemark, both unmarked; the build, round-trip and currency tests stay in test_catalog.py, marked slow.
    
    Recommendation: do it. Catalog-rule regressions are then caught in the dev suite, which matters once the catalog rule changes those rules.
    
    Cost: moved code only.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 26
  anchor_text: "26. The visual changelog parses card figures with its own regex"
  context_before: "ev suite The whole module is marked slow, though most of its tests draw nothing."
  context_after: "It reads the markup page.py writes, with its own pattern."
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    Issue: visual_changelog.py:26 has its own pattern for the card markup that page.py:207-208 writes.
    
    Proposal: one figures(page_text) in page.py, next to the code that writes them.
    
    Recommendation: do it.
    
    Cost: about 10 lines.
  replies:
    - author: Claude
      timestamp: 2026-10-25T16:36:16Z
      body: |
        Done in sskaye/forgegraph#9.
- id: 27
  anchor_text: "Not a refactoring"
  context_before: "res with its own regex It reads the markup page.py writes, with its own pattern."
  context_after: "Found in passing, not seen in use, so deferred: direct labels are placed after s"
  author: Claude
  timestamp: 2026-10-25T12:59:06Z
  resolved: false
  body: |
    For the record only. place_interior leaves key artists out of both the points and the texts it avoids (labels.py:150, 204), and direct labels are placed after style keys (xy.py:795-822), so a direct label could land on a style key; lint catches only text overlapping text. Not seen in any eval or report, so deferred as the audit's rule says. If it's ever seen, the fix belongs in finding 16's obstacles.
-->
