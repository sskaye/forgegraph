# FAQ

## What kinds of graphs can ForgeGraph make?

One graph type for now, `xy`: lines, markers and bars, with series stacked or side by side, and bars upright or on their side. Layers draw reference lines and bands, error bars and notes over it, and [layouts](../guides/layouts.md) put several graphs into one figure or a dashboard of tabs. The [Gallery](../gallery.md) shows examples. More graph types are planned; if there's one you need, [open an issue](https://github.com/sskaye/forgegraph/issues).

What no graph type can draw can be drawn with matplotlib on `fg.blank(theme, format)`, a canvas in the theme's look, and it's watermarked as non-standard.

## Which theme settings can I change from a GraphSpec?

The ones the theme marks `!var`. The ones it marks `!fix` are its house style, and setting one in a GraphSpec is an error. The built-in theme fixes the fonts, the colors, line styles, marker shapes and fills, the background, the grid, and the ticks' direction and placement, and leaves most sizes, weights, the legend and the layers' look to each GraphSpec. `forgegraph explain <graphspec>` shows every value, whether it's fixed and which file set it, and the [built-in pack's catalog](https://github.com/sskaye/forgegraph/blob/main/catalog/forgegraph_default.html) shows what changing each one does.

## How do I change the color palette or the font?

With a theme of your own. A theme in a pack can extend the built-in one and change its `series.colors` or `text.font`; a GraphSpec then names that theme. [Themes, formats and packs](../guides/themes-formats-packs.md) shows how.

## What size and resolution are graphs saved at?

The built-in `compact_format` draws a graph 150 mm wide, with its height following from the plot area's aspect ratio, at a base text size of 18 pt, and saves a PNG at 600 dots per inch. `wide_format` is twice as wide, for layouts. The file types are png, jpg, tiff, svg, pdf and html, set by `output.file_types` in the format or the GraphSpec.

## Can I annotate a graph?

Yes, with layers: a `reference` layer draws a target line, a line at the data's mean, or a band, with a label, and a `note` layer writes a short block of text in or around the plot. See [Layers](../guides/layers.md).

## What can error bars show?

The spread of the rows each point stands for: their standard deviation (the default), standard error, the 95 % confidence interval of the mean, a percentile, and others, times a multiplier. Or a fixed distance, or distances from columns of your data, which may differ below and above. See [Error bars](../guides/layers.md#error-bars).

## Can ForgeGraph put several graphs into one figure?

Yes: a layout arranges GraphSpecs in a grid, with tiles that can span rows and columns, for a figure in a paper, or in tabs, for a dashboard. See [Layouts and dashboards](../guides/layouts.md).

## Can a dashboard re-render by itself every morning?

Yes: a schedule file lists what to render and when, and `forgegraph job run` renders it once. Whatever schedules commands where you work, such as cron, launchd or Task Scheduler, runs that command at the schedule's times. See [Schedules](../guides/schedules.md).

## Does ForgeGraph read CSV or Excel files?

No: it draws a pandas DataFrame, saved as a Parquet file or passed in from Python. Reading and preparing the data is up to you, which keeps the GraphSpec about the graph. pandas reads CSV and Excel, and `df.to_parquet` saves the result.

## Why is my graph watermarked?

It's non-standard: drawn with a pack that only a folder config lists, not the main config, or drawn on `fg.blank`. Listing the pack in the main config makes it standard. See [Configs](../guides/configs.md#non-standard-graphs).

## Why didn't ForgeGraph just draw something close to what I asked?

A GraphSpec that can't be drawn as written is an error that says what to change. ForgeGraph never substitutes something else, such as series names drawn over the data, because a graph that silently isn't what was asked for is worse than an error.

## Do I need an agent to use ForgeGraph?

No. The `forgegraph` command and the Python API do everything the agent skill does; the skill lets an agent do it for you, from your data to a finished graph.

## Why does my agent offer to file a feature request?

When it made something ForgeGraph couldn't draw, or a watermarked graph, the agent skill asks whether you'd like a request filed for what was missing, so it can be added. It files one only if you say so.

## Do the HTML pages need a web server?

No: a page is one file, with its figures, fonts and record inside it, and opens from a folder or an attachment. Its tabs work where its scripts don't run. The readouts on data points and the stale banner need the scripts to run.

## Who owns the graphs I make?

You do. ForgeGraph is [MIT-licensed](https://github.com/sskaye/forgegraph/blob/main/LICENSE), and no attribution or licence terms apply to graphs and other output you make with it.
