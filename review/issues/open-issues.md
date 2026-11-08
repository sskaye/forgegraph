# Open issues

Last updated: 11/07/26

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
