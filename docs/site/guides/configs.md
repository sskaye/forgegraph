# Configs

A **config** lists the packs that may be used: their themes, formats, GraphSpecs, layouts and schedules. It's how a person or an organization requires its house style, and how a graph made outside it is marked.

```toml
packs = ["forgegraph_default", "./lab"]
```

Built-in and pip packs are listed by name, and folder packs by their path from the config file. `forgegraph schema config` lists the settings.

## The main config and folder configs

- **The main config**, `~/.config/forgegraph/config.toml` on every platform, or the file the `FORGEGRAPH_CONFIG` environment variable names, applies to all work. ForgeGraph writes it, listing the built-in pack, the first time a command reads the configs, such as `catalog` or `render`, and never overwrites it.
- **A folder config**, `forgegraph.toml`, applies to the files in its folder and in every folder below it. A file uses the nearest one: in its own folder, or else in the closest folder above it.

When both apply, a file may use only the packs the folder config lists. The configs are found from the file being drawn, not from the folder a command is run in, so a scheduled run is checked the same way as one by hand. `forgegraph catalog` and `forgegraph pack-notes` take `--folder` to show what may be used in another folder.

The example paper figure's folder has a config listing the built-in pack and its own journal pack:

```toml
--8<-- "examples/layouts/paper/forgegraph.toml"
```

## Non-standard graphs

A pack that a folder config lists but the main config doesn't still works, but it's **non-standard**: whatever is drawn with it is watermarked, the record saved in the file names the pack, and ForgeGraph's commands say so:

```text
Non-standard: pack 'acme' isn't in the main config (~/.config/forgegraph/config.toml), so whatever is drawn with it is watermarked
```

That way you can make and try a pack without changing an organization's main config, and nothing drawn with it passes as standard. List the pack in the main config to draw it as standard. A folder config can't give a pack the name of one the main config lists or a built-in pack's, so a folder can't swap an organization's pack for its own copy.

What's drawn on `fg.blank`, a themed canvas for drawing with matplotlib what no graph type can, is always non-standard, and watermarked the same way.

## Building on other packs

A config limits what a drawn file may name, not what a pack may build on. A pack's specs may extend specs in any pack a config that applies lists, or in an installed pip pack, even one a GraphSpec may not use. A spec made by extending is usable only if its own pack is allowed.
