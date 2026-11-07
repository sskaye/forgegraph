# Open issues

Last updated: 11/07/26

## [#119](https://github.com/sskaye/forgegraph/issues/119): hover readouts for graphs embedded in another page

- **Filed by:** CoryONeill.
- **Summary:** the readouts' data for graphs placed on the author's own page, along with #128, which asks for the marks and their data rows for an app. The author now re-renders each GraphSpec, reads the artists' positions from matplotlib, and writes a hover script.
- **Verification:** confirmed. `forgegraph.drawing.readout.marks` finds this data, but it isn't public, so anyone using it depends on ForgeGraph's internals. The script is written into ForgeGraph's own page and looks for an `<img>`, so it wouldn't work on an inline SVG as it stands. #80 left a public record of the marks out until someone needed it outside an HTML page, and now someone does.
- **Proposal:** #119 and #128 are one change. `Graph.marks()` returns a list with one item for each data point drawn, and `Graph.plot_area` gives the plot's box. Each item has:
  - its series' name and x and y values;
  - where it is, as fractions of the figure from the top left;
  - its marker's radius, or for a bar or cell, its box;
  - its readout's lines, as (name, value) pairs;
  - the positions in the data of the rows it was drawn from: one for a plain point, several for an aggregated one.

  With row positions, two rows at the same x and y can be told apart, and a caller can look up an id column itself. The script, one of:
  1. Leave it out. The author keeps their own, which already works.
  2. Add `forgegraph.hover_script()`, or an `html_fragment` output, which the issue offers as alternatives. The script would have to work on an inline SVG as well as an `<img>`.

  Recommendation: 1. The data is what the author can't get reliably, and a public script would be one more thing to keep stable. For now this covers a `Graph`, and a layout's tiles can follow if someone asks.
- **Why the author needs it:** the readouts work only on ForgeGraph's own HTML page. The author puts 64 to 96 graphs on a page of their own, with the toolbar, pickers and toggles that our page lacks, so our readouts never reach them. Their workaround reads matplotlib's internals. If our page gains the view controls under #116, the author may be able to use it, and this need goes away. #128 is for an app that edits graphs, which #131 leaves for Studio.

  Recommendation (revised): hold #119 and #128 until the view controls are decided.
- **Decision:** decline for now, and #128 with it, as it's the same change.

## [#126](https://github.com/sskaye/forgegraph/issues/126): size, color, shape and opacity for single points

- **Filed by:** CoryONeill, for an app where a reader picks out single measurements.
- **Summary:** one point made bigger, recolored, reshaped or faded, without changing the rest of its series. The author moves the point's value into a new column and draws that as its own series, which needs the key turned off (#127), breaks a line at the point, and doesn't work on an aggregated series.
- **Verification:** confirmed. `marker.size` and `opacity` take one number per series, and a column is an error. A color column doesn't set a color either, because each of its values takes the next palette color, so a chosen color for one point isn't possible that way. Copying the value into the new column, instead of moving it, would keep the line whole and draw the highlight on top.
- **Proposal:** one of:
  1. Hold this one, and build #127. A highlight is then a second series, drawn from a copied column and left out of the key. This doesn't cover an aggregated series.
  2. Let `marker.size` and `opacity` take a column whose values are the sizes and opacities themselves. This doesn't cover a chosen color.
  3. The issue's `points` block, with styles for each row by an id column. This covers everything asked, but it's a second way of styling that every mark type has to respect.

  Recommendation: 1. It meets the stated need with one small parameter. The rest comes from the app in #131, whose controls belong with Studio. If aggregated highlights turn out to matter, 3 is the one to consider.
- **Revised, with #127 declined:** a highlight belongs in a layer, as you say. If this is wanted, it would be a new layer type that draws chosen rows again on top, picked by an id column, with its own marker size, color, shape and opacity, and never in the key. It works for an aggregated point too, if it picks by the point's rows.

  Recommendation (revised): hold, and build the highlight layer if someone asks again.
- **Decision:** hold. A highlight layer is built if someone asks again.

## [#127](https://github.com/sskaye/forgegraph/issues/127): leave a series out of the key

- **Filed by:** CoryONeill.
- **Summary:** a series that's drawn but not named, such as a highlight or helper series.
- **Verification:** reproduced on 0.7.0: a helper series named `__pt0` appears in the key. The only choice is to drop the whole key.
- **Proposal:** a new series parameter, `legend.show` (true or false, default true). With false, the series is left out of the key and gets no direct label. It's still in a readout, under its name. The code already has this case, because a series colored on a scale has no name to label.

  Recommendation: this proposal.
- **Examples:** the cases I can think of are better done another way:
  1. A highlight: a layer, as you say (see #126).
  2. All the data in light grey behind a highlighted group: the grey series is better named, such as "Other runs", so the key explains it.
  3. Raw points and their mean drawn as two series colored by the same column: the key already shows each group once.

  Recommendation (revised): decline.
- **Decision:** decline, unless the author's examples show otherwise.

## [#128](https://github.com/sskaye/forgegraph/issues/128): drawn marks and the plot area from the Python render

- **Filed by:** CoryONeill.
- **Summary:** where each mark is drawn and which row of data it came from, for an app with hover readouts, right-clicks and per-point editing. Matching points back to rows by their values fails when two rows share an x and a y.
- **Verification:** confirmed. See #119.
- **Proposal:** the same change as #119: `Graph.marks()` and `Graph.plot_area`.

  Recommendation: build it with #119 and close both.
- **Decision:** decline for now, with #119.

## [#129](https://github.com/sskaye/forgegraph/issues/129): smaller SVG output

- **Filed by:** CoryONeill, for a 96-graph page that came to 17.7 MB against a host's limit of 16 MB.
- **Summary:** shorter coordinates and no whitespace in SVG output. The author does this with regular expressions, and got the page to 14.5 MB with no visible change.
- **Verification:** measured on a graph of 170 points and a band, 79 kB. Removing whitespace saves about 6 %, and rounding coordinates to 2 decimals about 5 %. The metadata block, 14 % of that file, is ForgeGraph's provenance record, so removing it means `load` can no longer recover the GraphSpec. A setting for that already exists: on a smaller graph, `provenance.level: minimal` took the file from 47 kB to 39 kB.
- **Proposal:** one of:
  1. Always write SVG with coordinates to 2 decimals and no whitespace between tags, with no new parameter. It saves about 10 %, and 1/100 of a point can't be seen at any normal size. The docs point to `provenance.level` for pages where size matters most.
  2. Parameters for `precision` and `minify`, as the issue shows. These allow 1 decimal, which saves about 1 % more, but they are two settings no one needs to think about otherwise.

  Recommendation: 1. It helps every SVG and every HTML page, which holds SVGs. I'd check by drawing the files before and after, because I've only measured their sizes.
- **Revised:** the code is small, about 15 lines rewriting the SVG text, but it's one more thing to keep working through matplotlib upgrades, for 10 %. The author's page needed under 10 % to fit their limit, and `provenance.level: minimal` saves more than that today: 18 % on the 47 kB graph above.

  Recommendation (revised): decline, and point the author to `provenance.level`.
- **Decision:** decline.

## [#130](https://github.com/sskaye/forgegraph/issues/130): one setting for a graph's mark type

- **Filed by:** CoryONeill.
- **Summary:** `marks: scatter`, `line`, `line_markers` or `bar` in place of setting `line.show`, `marker.show` and `bar.show` on each series.
- **Verification:** confirmed that each mark type can be drawn, and that switching means setting up to three values on each series. It adds no new drawing, only a shorter way to write it, and the need comes from the reader-facing control in #131.
- **Proposal:** one of:
  1. Decline. You rejected scatter and line presets in the phase 5 review, because two fixed parameters are just as easy. A caller's code sets the three values on each series in a short loop.
  2. A GraphSpec parameter, `marks`, as the issue shows. It would need a rule for a series that sets its own marks.

  Recommendation: 1, unless a real use appears from someone writing GraphSpecs by hand.
- **Decision:** decline.

## [#131](https://github.com/sskaye/forgegraph/issues/131): reader edits saved as an overrides file

- **Filed by:** CoryONeill.
- **Summary:** a reader adjusts a graph on the page (axis range, chart type, markers, single points), and the changes are kept in a small file applied on top of the GraphSpec, so a rebuild keeps them. The author has built a local app that does this.
- **Verification:** confirmed that the HTML page is read-only and that a GraphSpec has no such file. `extends` can layer one GraphSpec on another, but it names a GraphSpec in a pack, not a file beside it. A Python app can already apply its overrides to the GraphSpec before calling `fg.render`, which is what this one does. This is close to what the architecture plans for Studio (D14): a local app whose options panel changes a graph, and which writes the result back to the spec. Studio comes after everything else works.
- **Proposal:** one of:
  1. No change for now. The file stays with the app that writes it. `Graph.marks()` (#119, #128) and the named SVG (#117) give that app what it can't get otherwise, and the page's controls wait for Studio.
  2. A GraphSpec parameter, `overrides`, naming a file that's applied last, with no controls on the page. This saves an app a few lines, but it adds a second way to layer specs beside `extends`.
  3. As 2, with controls on the page that download the file or post it to a URL. This starts Studio inside the HTML page, ahead of its turn.

  Recommendation: 1. It keeps Studio's work in its place and still helps this author directly. This author's app is a useful source of requirements when Studio comes up, so it's worth keeping these issues in mind for then.
- **Decision:** 1, no change.
