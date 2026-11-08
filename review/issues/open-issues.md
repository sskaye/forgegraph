# Open issues

Last updated: 11/08/26

## [#142](https://github.com/sskaye/forgegraph/issues/142): a reference line's label can't be placed inside a reference band (0.8.0 regression)

- **Filed by:** sskaye.
- **Summary:** in 0.8.0, a reference line's label can't be placed when another reference layer's band surrounds the line, such as a mean line inside its ±1 SD band. Every position fails, auto or chosen. 0.7.0 places it.
- **Verification:** reproduced on 0.8.0 with the issue's GraphSpec: auto, `start_below` and `end_above` all fail. Without the band layer it draws. With the band's `fill.color: None` it draws too: its two edge lines are far enough from the label. With `fill.opacity: 0` it fails, so the issue's "band without fill" was likely made that way: a fill you can't see still counts.
- **Root cause:** the #132 change. Keys, notes and reference labels keep clear of every band's fill. In 0.8.0 I let a reference label sit on its own layer's band, so a band's two lines could label inside it, but a band drawn as a separate layer, as here, still blocks the label. Separately, a fill with opacity 0 is still sampled as drawn content, for keys and notes as well as labels.
- **Proposal:** one of:
  1. A reference label ignores every band's fill; fills count only for keys and notes, as the #132 decision named first. A band's edge lines still count, as every line does. And a fill with opacity 0 counts for nothing.
  2. A reference label ignores a band's fill only where its line lies inside that band, and keeps clear of bands it's outside of. The opacity fix as in 1.

  Recommendation: 1. A band is light by design (opacity 0.15), so a label on it reads well, and the line is what the label is about. 2 needs a rule for lines that cross a band's edge, for a case no one has asked for. Either way, it's a bug fix released as 0.8.1, with the issue's GraphSpec as a test, filled and at opacity 0.
- **Decision:**

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
