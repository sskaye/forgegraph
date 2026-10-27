# Refactoring proposals

A pass looking only for structure: modules that do too much, the same logic written twice, wrong boundaries, and loose data where a small type would simplify. Every proposal keeps behaviour identical; drawing changes are checked byte-identical, as in the audit's batch 2.

Each finding has a comment with the issue, the proposal (with options where there are real alternatives) and my recommendation. Reply on each; nothing changes until you have.

Order I'd do them in, if you agree: the spec layer (1 to 8), then drawing (9 to 18), then the CLI, catalog and tests (19 to 26), with 19 before the catalog rule and all of them before the renames.

## Specs, graphs, layouts and jobs

### 1. spec/documents.py does five jobs

The registry, resolution, validation, pack permissions and layers are in one 956-line module, which imports spec/layout.py lazily while layout imports it back.

### 2. "The specs a document names" is written a dozen times

That a GraphSpec names a graph type, theme and format, and a layout a format, is re-derived in about twelve places across four modules.

### 3. Resolved values come in three shapes

Resolution returns values with their source, values with whether they're fixed, or plain values, and about twenty call sites index or convert between them.

### 4. A loaded document travels as a tuple

The document, its registry and its folder are passed as three values through about fifteen signatures, and "a relative path is found from the file that sets it" is written three times.

### 5. graph.py is also the shared library

Layouts, the blank canvas and jobs import inspection, saving, provenance, data reading and spec checks from graph.py, and the provenance record is assembled three times.

### 6. The end of a render is written twice

A graph and a layout's tile finish a render with the same steps, line for line, and a tile copies a prepared graph's fields one by one.

### 7. The CLI and jobs branch on "is it a layout"

The same check appears nine times, choosing between two code paths that differ only in small ways.

### 8. Small duplicated constants

The kind-to-folder map, the base pack's name and its folder are each defined more than once.

## Drawing

### 9. Helpers in xy.py reach other modules as callbacks

Layers, marks and the color bar receive general helpers from xy.py as lambdas and extra parameters.

### 10. The render passes are driven twice

A graph and a layout each run the same lay-out, place and label passes, through a five-function protocol each graph type must provide.

### 11. The layout settle loop is written twice

One graph's layout and a layout's grid run the same measure-and-settle algorithm, and figure.py mixes the figure classes with measuring.

### 12. A series' stack, shifts and look travel in parallel lists

Three lists are zipped together at five sites, and whether a series is the benchmark is decided four times.

### 13. The four style dimensions are listed in five places

Color, line style, marker shape and marker fill each appear in five separate lists in xy.py.

### 14. xy.draw is one 170-line function

It stacks, draws marks, draws layers, sets the axes and decorates, in one function sharing all its locals.

### 15. axes.py holds three modules

Axis data types, the whole calendar subsystem and the exception class other modules need are in one 675-line module.

### 16. What a label must stay clear of is defined four ways

Each kind of placed text builds its own list of obstacles.

### 17. Orientation is passed as strings

About 40 conditionals choose between x and y.

### 18. A theme font is built the same way at eight sites

The same three-part expression builds a font from the theme at each.

## CLI, catalog, tests and scripts

### 19. The catalog card loop does four jobs

One function reads the catalog file, draws, builds the table and places the cards, and the perturbation test re-implements the placement.

### 20. Tests write spec documents and projects by hand

About 30 documents are written out with their full header, the same project setup appears six times, and two copies of a document builder exist.

### 21. Forgemark's file format is defined in five places

The comments-block marker, the anchor regex, carrying comments onto a rebuilt page and stripping review markup are each written more than once.

### 22. Every CLI command repeats its failure and output code

Each command catches its errors and prints JSON or text in its own copy of the same few lines.

### 23. Baselines and their regression check are drawn separately

The script that draws the image baselines and the test that compares against them each have their own drawing code.

### 24. The skill evals' grade function is 270 lines

It checks about 25 expectations inline, and draws and resolves the final GraphSpec twice.

### 25. test_catalog.py keeps fast tests out of the dev suite

The whole module is marked slow, though most of its tests draw nothing.

### 26. The visual changelog parses card figures with its own regex

It reads the markup page.py writes, with its own pattern.

## Not a refactoring

Found in passing, not seen in use, so deferred: direct labels are placed after style keys, and their search doesn't avoid keys, so a direct label could land on a style key.

