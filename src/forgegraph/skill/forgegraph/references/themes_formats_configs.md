# Creating or editing themes, formats and configs

A theme or format is a spec in a pack. ForgeGraph reads it only from a pack, and a GraphSpec can use it once a config lists the pack.

## Workflow

1. Select a base spec to build from: the theme or format closest to the request (`forgegraph catalog` lists them), or a base spec: `forgegraph_base/base_theme`, `forgegraph_base/base_format`, or `forgegraph_base/base_layout_format` for a layout.
2. Select the pack for the new spec: one the user names, or a new one (see Modifying or creating a pack).
3. Write the new spec in the pack's themes/ or formats/ folder, setting `extends` to the base spec and listing under `parameters` only the parameters you want to change. Each keeps the status it inherits; to change that, tag it `!fix` if a GraphSpec can't change it, or `!var` if it can (`width: !var 0.15`). A tag on a category applies to everything in it, and a tag with no value (`width: !var`) changes only the status. `forgegraph schema theme` and `forgegraph schema format` list every parameter, with its allowed values, default and description.
4. List the pack in the configs that apply to the GraphSpecs that will use it (see Configs). Ask the user before changing the main config, since it applies to all work. If the main config can't be changed, list the pack in a folder config: it works, but its graphs are non-standard (watermarked) until the main config lists it.
5. Render a GraphSpec that uses the spec: the one the user asked for, or a copy of examples/xy.yaml and xy.parquet with its theme or format changed. Rendering reports any problem with the spec, and `forgegraph explain <graphspec>` shows which values it set. Check the image looks as intended.

To edit a theme or format, change its file in its pack and raise its `version`, then do step 5.

## Modifying or creating a pack

A pack is a folder. It can be kept anywhere, and is usable once a config lists its path.

```
<pack>/
├── pack.yaml      # name, version, description, issues, requires
├── themes/        # one <name>.yaml per theme
├── formats/       # one <name>.yaml per format
├── graphspecs/    # optional, as are layouts/ and schedules/
├── references/    # optional: <note>.md, notes for the agent
└── fonts/         # optional: .ttf and .otf files its themes name
```

To modify a pack, add or edit the appropriate file.

To create a pack:
1. Create the folder where the user asks, or else in the folder holding the files that will use it.
2. Write pack.yaml. `forgegraph schema pack` lists its fields.
3. Add the needed specs, references, and fonts to their respective folders.

## Configs

A config lists the packs a GraphSpec may use, e.g. `packs = ["forgegraph_base", "./lab"]`. A folder pack is a path from the config file. `forgegraph schema config` lists the settings.

- The main config, \~/.config/forgegraph/config.toml (or the file FORGEGRAPH_CONFIG names), applies to all work. ForgeGraph writes it, listing the built-in packs, the first time a command reads the configs.
- A folder config, forgegraph.toml, applies to the files in its folder and in every folder below it. A file uses the nearest one: in its own folder, or else in the closest folder above it.
- When both apply, a file may use only the packs the folder config lists. A pack the main config doesn't list works, but it's non-standard: whatever is drawn with it is watermarked, and ForgeGraph's commands say so.
- A pack's specs may build on specs in any pack a config that applies lists, or in an installed pip pack, even if a GraphSpec may not use that pack.

