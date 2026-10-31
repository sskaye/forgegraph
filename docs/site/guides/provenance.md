# Provenance

Every file ForgeGraph saves records how it was made, inside the file itself, so a graph can be traced and drawn again: its GraphSpec, the specs it used and their versions, and the data file it read. The [provenance specification](../reference/specifications/provenance.md) lists every entry.

## What's recorded

The format's `provenance.level` sets how much each file records:

- **full**, the built-in formats' level: everything in minimal, every value the graph was drawn with, and the data file and `data.preprocessing` as the GraphSpec lists them.
- **minimal:** the ForgeGraph version, when the file was drawn, the GraphSpec without its data file and preprocessing, each spec used with its version and its pack's version, and whether the graph is non-standard, with the packs that make it so. It's for files that mustn't reveal where their data is.
- **off:** nothing.

A layout's files record the layout as it's written and, for each tab they show, each tile's GraphSpec file and the same entries as a GraphSpec's.

The record is one JSON document, stored where each file type keeps such things: a PNG text chunk, a JPEG comment, the TIFF image description, the SVG metadata, the PDF document information, and a script in an HTML page's head. It's invisible in the image.

## Reading it back

```bash
forgegraph load polarization.png --graphspec recovered.yaml
```

`load` shows what drew the file, and with `--graphspec`, writes its GraphSpec, with its `!var` and `!fix` tags, ready to draw again. From Python:

```python
import forgegraph as fg

record = fg.load("polarization.png")
record["graphspec"]  # the GraphSpec, with its !var and !fix tags
record["specs"]      # each spec used: its name, its version and its pack's version
```

A layout's record has the layout under `"layout"`, and its tiles under `"tabs"`.

## Keep the GraphSpec too

PowerPoint, Slack and other tools often strip a file's metadata when it's pasted or uploaded, and the record goes with it. Keep each graph's GraphSpec beside it, as the agent skill does, so the graph can be drawn again from either.

## Files that don't change

With the `SOURCE_DATE_EPOCH` environment variable set, its time is recorded as when the file was drawn, and the same GraphSpec and data give byte-identical PNG, SVG and PDF files, so saved graphs can be compared and kept in version control.
