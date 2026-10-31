# Troubleshooting

Every render lints the graph it drew and lists any issues, each under the name of its check. An issue doesn't stop the graph from being saved, but it means something in it is hard to read or isn't what the data says. A GraphSpec that can't be drawn at all is an error instead, which says what's wrong and what to change; [errors](#errors) below covers the common ones.

`forgegraph render --json` and `g.issues` in Python give each issue's check and message.

## Lint issues

### overlapping-text

Two texts' letters overlap, such as neighboring tick labels or a title and a key.

Make room: fewer ticks (`tick.algorithm: manual` with a larger `tick.step`), a shorter label or tick label format, a wider format (`figure.width`), or rotated x tick labels, where the theme lets a GraphSpec set `axis.tick.label.x_rotation`.

### clipped-text

A text runs past the figure's edge, so part of it is cut off, such as a long label placed outside the plot.

Shorten the text, place it inside the plot, or widen the format.

### key-over-data

A key covers a line or marker.

List other positions in `legend.key.positions`, put the key outside the plot with `legend.key.inside: false`, or name the series directly with `legend.method: direct`.

### too-many-groups

A column gives more groups than the theme has colors, line styles or marker shapes, so they repeat, and two groups look the same. The message names the column and the theme's list.

Draw fewer groups, give a second column another of the styles (such as `marker.shape`) so each group is told apart, or use a theme with more colors.

### log-axis-values

Values of 0 or below on a log axis can't be drawn, so they're left out. It's an error when the data has them; this issue comes from something drawn on the graph afterwards.

Use a linear scale, or leave those values out.

### outside-limits

Points lie beyond an axis's fixed `min` or `max`, so they aren't drawn.

Widen the limits, or set them to None so the axis fits the data.

### small-text

Some text is smaller than 6 pt, too small to read at the figure's size. The message names the smallest.

Make the format's `figure.base_size` larger: every text size is a multiple of it.

### font-fallback

A font the theme names isn't installed, so another is used, or a letter isn't in the theme's font, so it isn't drawn.

Install the font, or add its .ttf or .otf files to the pack's fonts/ folder. For a missing letter, write the text another way, or use a theme whose font has it.

### dropped-rows

Rows are left out of the graph, with the reason, such as `5 rows left out: missing x or y`. It's often expected: the CO₂ record in the [gallery](../gallery.md#dates) has months with no reading.

Check the rows are meant to be missing. `line.missing_values: gap` breaks a line where they are, instead of joining across them.

### dates-as-text

An axis's column is text that reads as dates or times, so it's drawn as categories rather than on a time axis.

Make it a date column when you write the Parquet file, for example with `pd.to_datetime`.

## Errors

### A parameter the theme fixes

```text
title.font: fixed by theme 'forgegraph_default/light_theme'
```

The theme marks this parameter `!fix`, so a GraphSpec can't change it; a theme keeps a house style that way. Use a theme that sets it as you want, or [make one](../guides/themes-formats-packs.md) that extends this theme and changes it. `forgegraph explain` shows which parameters are fixed.

### A pack the config doesn't allow

```text
specifications.theme: 'acme/acme' is in the pack 'acme', which ~/.config/forgegraph/config.toml doesn't allow
```

List the pack in the main config, or in a folder config for the files that use it. A pack only a folder config lists works but is non-standard: see [Configs](../guides/configs.md).

### Non-standard and watermarked

```text
Non-standard: pack 'acme' isn't in the main config (~/.config/forgegraph/config.toml), so whatever is drawn with it is watermarked
```

This isn't an error: the graph is drawn and saved, with a watermark. List the pack in the main config to draw it as standard.

### The data isn't Parquet

```text
data.file: 'runs.csv' isn't a Parquet file (ArrowInvalid)
```

ForgeGraph reads a DataFrame saved as Parquet, so preparing the data is up to you: read the CSV or spreadsheet with pandas, and save it with `df.to_parquet("runs.parquet")`. From Python, a GraphSpec whose `data.file` is None takes the DataFrame directly: `fg.render(spec, data=df)`.

### A column that isn't there

```text
axis.x.data.column: no column 'Current' in the data; columns are Cell, Run, ...
```

The message lists the columns the data has. Column names must match exactly, including units and capitals.

### An unknown parameter

```text
titel: unknown category; did you mean 'title'?
```

A misspelled or misplaced parameter, with the nearest one ForgeGraph knows. The [specifications](../reference/specifications/index.md) list every parameter in its place.

### No way to name the series

```text
legend.method: auto, but no labelling method fits (key tried); put the key outside (legend.key.inside: false), ...
```

No method the theme allows can name the series without covering the data, and ForgeGraph never draws names over the data instead. Do one of the things the message lists, such as putting the key outside the plot.

### Untagged parameters

```text
extends: None, so every parameter needs a !var or !fix tag, on it or a category above it; untagged: ...
```

A GraphSpec that extends nothing must tag its parameters, which says whether a GraphSpec that extends it may change them. `parameters: !var` tags them all.
