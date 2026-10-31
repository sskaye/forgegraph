# Themes, formats and packs

A **theme** fixes the look of a graph: its fonts, colors, lines, keys and the rest. A **format** sets its destination: the figure's size, the base text size, and the file types and resolution it's saved in. Both come from a **pack**, a folder or pip package of specs, and a GraphSpec names them `pack/name`.

ForgeGraph's built-in pack, `forgegraph_default`, has a theme, `light_theme`, and two formats: `compact_format` for single graphs and `wide_format`, twice as wide, for layouts. The [built-in pack's pages](../reference/built-in-pack/index.md) show them whole, and `forgegraph catalog` lists every theme and format that may be used where it's run.

## A pack

A pack is a folder like this, with the folders it needs:

```text
lab/
├── pack.yaml      # name, version, description, issues, requires
├── themes/        # one <name>.yaml per theme
├── formats/       # one <name>.yaml per format
├── graphspecs/    # GraphSpecs to extend; layouts/ and schedules/ likewise
├── references/    # notes about the pack's specs, for people and agents
└── fonts/         # .ttf and .otf files its themes name
```

pack.yaml names the pack, gives its version, and says where to file requests about its specs:

```yaml
--8<-- "docs/examples/packs/lab/pack.yaml"
```

`requires` is the ForgeGraph versions the pack works with, as pip writes them. A pack holds YAML, Markdown, Parquet data and fonts, and never code. A [config](configs.md) must list a pack before its specs can be used.

A pack can also be a pip package that declares a `forgegraph.packs` entry point, so it's installed, versioned and pinned like any other dependency.

## A theme

A theme usually starts from another and lists only what it changes. This one gives the built-in theme Paul Tol's bright colors, horizontal grid lines and a bold title:

```yaml
--8<-- "docs/examples/packs/lab/themes/lab_theme.yaml"
```

Each parameter keeps the `!fix` or `!var` it inherits, which says whether a GraphSpec may change it. A theme can change that with a tag: `width: !var 0.15` makes a parameter variable, and a tag on a category applies to everything in it. The built-in theme fixes the fonts and the colors, so graphs drawn with it look alike, and leaves sizes such as the markers' to each GraphSpec.

The theme's categories are its general `text` and `line`, which the other text and lines take their defaults from; the `background`; the `title`; the `axis` titles, ticks and tick labels; the `plot_area` and its `grid`; how every `series` looks, including its colors, line styles, marker shapes and fills; the `legend` methods, key and color bar; each `layer`'s look; the `watermark` drawn on non-standard graphs; and the `footnote`. The [theme specification](../reference/specifications/theme.md) lists every parameter.

`series.colors` takes a named palette (`okabe_ito`, `tol_bright`, `tol_muted`, `tableau_10` or `color_blind`) or a list of hex colors, given to the series or their groups in order.

**Fonts.** A theme's `text.font` names a typeface. ForgeGraph bundles Roboto and IBM Plex Serif; any other must be installed on the machine, or be in the pack's fonts/ folder. A font that's missing is drawn with another, and the lint says so.

## A format

```yaml
--8<-- "docs/examples/packs/lab/formats/poster.yaml"
```

- **figure.width** and **figure.height** are in millimetres. With one of them `auto`, it follows from the other and the theme's plot area aspect ratio.
- **figure.base_size** is in points. The sizes of text, lines, ticks and gaps are multiples of it, so a larger base size scales the whole graph's text and lines together.
- **output.file_types** are png, jpg, tiff, svg, pdf and html; **output.dpi** is the resolution of png, jpg and tiff.
- **provenance.level** is how much each saved file records about how it was made (see [Provenance](provenance.md)).

The polarization curves, drawn with the lab pack's theme and format:

```yaml
--8<-- "docs/examples/lab_polarization.yaml"
```

![The polarization curves in Paul Tol's colors, with horizontal grid lines, on a wider figure.](../images/lab_polarization.png){ width="560" }

## Checking a theme or format

Draw a GraphSpec that uses it. Drawing reports any problem with the spec, and `forgegraph explain <graphspec>` shows each value and which file set it. To change a spec that's in use, edit its file and raise its `version`, which every saved file records.

The [acme example pack](https://github.com/sskaye/forgegraph/tree/main/examples/packs/acme) is a fuller one, in a deliberately different style: a theme, a slide format, a GraphSpec, a layout and a schedule to extend, and a reference note. The [Gallery](../gallery.md) shows its look.
