# Packs and config: research for the Phase 6 specification

Input for the Phase 6 proposal: the packs and config specification, pack discovery, config, namespacing, `explain` origins and `forgegraph reference`. Sources are listed with each claim. "Verified" means I checked the claim in the CPython source or the project's own environment, not only in the docs.

## 0. Where ForgeGraph stands today (repo facts)

- `spec/documents.py` builds a `Registry` from two layers:
  - **built-in**: `files("forgegraph") / themes|formats|graph_types|graphspecs`;
  - **project folder**: `themes/`, `formats/` and `graphspecs/` under a root. `graph.py:_root` finds the root as the parent of a `graphspecs/` folder, or else the GraphSpec's own folder.
- `Registry.add` keys each file by its bare `name`. A project file named `default` therefore **silently replaces** the built-in `default`. That conflicts with the "error, don't fall back" rule, and Phase 6 has to decide how it works.
- Origins already exist, as `Resolved.origin`, e.g. `"theme 'journal', under xy"`. They name the file but not its layer or path.
- `explain` prints `path = value (fixed|variable, origin)`, and `--json` gives `kind / parameter / value / fixed / set_by`.
- `specifications.theme` and `specifications.format` in the GraphSpec definition default to `default`. Config can only take effect if "unset" stays distinguishable from "default".
- Three places still use older names:
  - D4 draws a pack with `presets/`, but the decision log made presets GraphSpecs that others extend (`graphspecs/`).
  - D4 names the command `forgegraph reference house`.
  - Packs need `catalogs/` too: Phase 3 made a catalog file per theme, format and graph type, and Phase 6 builds "preset and theme catalog tabs from packs".
- `version` in every definition file is `[int]; The version number of the specification`. A pack's version is a release version (semver), which is a different thing.
- Dependencies: `packaging` is already installed through matplotlib (`requires('matplotlib')` gives `packaging>=20.0`, verified), so PEP 440 specifiers cost nothing. `platformdirs` is in the venv but isn't a declared dependency. `tomllib` is in the standard library from Python 3.11 ([PEP 680](https://peps.python.org/pep-0680/)).

## 1. Discovering plugins without importing them

**The established mechanism is entry points.**
- Entry points are metadata in `*.dist-info/entry_points.txt`, an INI file, read at run time with `importlib.metadata` ([PyPA entry points spec](https://packaging.python.org/en/latest/specifications/entry-points/)).
- An object reference may name a module only, with no `:attr`; pytest plugins work this way (same spec).
- Name conflicts are the host's problem: "Within a distribution, entry point names should be unique". When different distributions use the same name, the consumer decides (same spec).
- The PyPA plugin guide lists three discovery methods: naming convention, namespace packages and entry points. With entry points, nothing is imported until `.load()` ([PyPA, Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)).
- `EntryPoint` has `.name`, `.group`, `.value`, `.module`, `.attr` and `.dist`. `Distribution.files` and `locate_file()` give the installed files; `files` is `None` when the RECORD is missing ([importlib.metadata docs](https://docs.python.org/3/library/importlib.metadata.html)).

**"Without importing" has two traps.**
1. `importlib.resources.files("pkg")` **imports `pkg`** and so runs its `__init__.py`. The docs only say the anchor is "a module object or a module name" ([importlib.resources](https://docs.python.org/3/library/importlib.resources.html)). The source settles it (verified in the project's Python 3.12): in `importlib/resources/_common.py`, `resolve` registers `importlib.import_module(cand)` for strings.
2. `importlib.util.find_spec(name)` doesn't import a top-level name. For a dotted name, "the parent module is automatically imported" (verified with `find_spec.__doc__`; [docs](https://docs.python.org/3/library/importlib.html#importlib.util.find_spec)).

**Existing practice that fits ForgeGraph's case.**
- **napari's npe2** declares a data manifest through an entry point: `napari.manifest`, with value `example_plugin:napari.yaml` ([napari manifest reference](https://napari.org/stable/plugins/technical_references/manifest.html)).
- npe2 finds the file with `util.find_spec(module)` and `spec.submodule_search_locations`, then parses the YAML, without executing the module ([npe2 source, `_from_entrypoint`](https://github.com/napari/npe2/blob/main/src/npe2/manifest/schema.py)).
- That is the closest established precedent for "a data manifest in a pip package, read without importing".

**How others do it.** They all import, which is why ForgeGraph can't copy them as they are:

| Tool | Mechanism | Imports plugin code? |
| --- | --- | --- |
| pytest | `pytest11` entry points, auto-loaded at startup; `PYTEST_DISABLE_PLUGIN_AUTOLOAD` turns this off ([docs](https://docs.pytest.org/en/stable/how-to/writing_plugins.html)) | yes |
| flake8 | `flake8.extension` entry points ([docs](https://flake8.pycqa.org/en/latest/plugin-development/registering-plugins.html)) | yes |
| Sphinx themes | `sphinx.html_themes` entry point to a module whose `setup(app)` calls `add_html_theme()`; the theme itself is data, `theme.toml` from 7.3 ([docs](https://www.sphinx-doc.org/en/master/development/html_themes/index.html)) | yes (the `setup` module) |
| matplotlib package styles | `plt.style.use("mypackage.presentation")` reads `mypackage/presentation.mplstyle` from an importable package ([docs](https://matplotlib.org/stable/users/explain/customizing.html#distributing-styles)) | yes (through importlib.resources) |
| JupyterLab prebuilt extensions | files copied to `<sys-prefix>/share/jupyter/labextensions/<name>`, plus `install.json` ([docs](https://jupyterlab.readthedocs.io/en/stable/extension/extension_dev.html)) | no (found by folder), but tied to install prefixes |
| napari npe2 | entry point to a YAML manifest, located through `find_spec` | no |

**Namespace packages** ([PEP 420](https://peps.python.org/pep-0420/)) carry no code, but the PyPA guide warns that "one bad plugin could cause the entire namespace to break". A single stray `__init__.py` turns the namespace into a regular package and runs code. Not recommended.

**Security for data-only plugins.**
- Not importing is a guarantee about what *ForgeGraph* does. It is not a sandbox.
- Installing is still a trust decision. A wheel's `.pth` file can run `import` lines "at Python startup … regardless of whether a particular module is actually going to be used" ([site docs](https://docs.python.org/3/library/site.html)), and building an sdist runs build-backend code.
- What ForgeGraph controls:
  - **YAML is loaded with a safe loader.** ruamel's `typ="safe"` is already used; unsafe loaders can construct arbitrary objects, see [CVE-2017-18342](https://nvd.nist.gov/vuln/detail/CVE-2017-18342) for PyYAML's `yaml.load`.
  - **Every path a pack names stays inside the pack root**, including fonts and catalogs. Reject `..`, absolute paths and symlinks that leave the root.
  - **Only known file kinds are read**: `.yaml`, `.md`, `.ttf`/`.otf`.
  - **Reference notes are treated as untrusted content.** This is "indirect prompt injection"; OWASP's mitigation is "Separate and clearly denote untrusted content" ([OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)).

## 2. Config locations, layering and showing origins

**User config locations.**
- [XDG Base Directory spec](https://specifications.freedesktop.org/basedir-spec/latest/): `$XDG_CONFIG_HOME`, by default `~/.config`.
- [platformdirs](https://platformdirs.readthedocs.io/en/latest/platforms.html) `user_config_dir`:
  - Linux `~/.config/App`;
  - macOS `~/Library/Application Support/App`;
  - Windows `C:\Users\<User>\AppData\Local\<Author>\App`.
  - It honours `XDG_CONFIG_HOME` on macOS too ([platformdirs](https://platformdirs.readthedocs.io/en/latest/)).
- Python CLI tools often use `~/.config` on macOS as well:
  - **uv**: `~/.config/uv/uv.toml` on macOS and Linux, `%APPDATA%\uv\uv.toml` on Windows ([uv docs](https://docs.astral.sh/uv/concepts/configuration-files/));
  - **Black**: `$XDG_CONFIG_HOME/black` on Unix-likes ([Black docs](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html));
  - **matplotlib**: XDG on Linux, `~/.matplotlib` elsewhere ([docs](https://matplotlib.org/stable/users/explain/customizing.html));
  - **pip**: checks `~/Library/Application Support/pip` and then `~/.config/pip` on macOS ([pip docs](https://pip.pypa.io/en/stable/topics/configuration/)).
- **D4's `~/.config/forgegraph/config.toml` matches uv.** Recommended: XDG on macOS and Linux, `%APPDATA%\forgegraph\config.toml` on Windows, and an env var override.

**Project config discovery.**
- **uv** walks up from the current directory to the nearest `uv.toml`/`pyproject.toml`, skips a `pyproject.toml` with no `[tool.uv]`, and prefers `uv.toml` in the same folder ([uv](https://docs.astral.sh/uv/concepts/configuration-files/)).
- **Ruff** uses the closest config file to each file, resolves relative paths from that config's folder, and doesn't merge parents unless asked to with `extend` ([Ruff](https://docs.astral.sh/ruff/configuration/)).
- **Black** starts at the files' common base, walks up and stops at `.git`, `.hg` or the filesystem root ([Black](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html)).
- **EditorConfig** walks up until `root=true`; closer files win ([editorconfig.org](https://editorconfig.org/)).
- `[tool.<name>]` in `pyproject.toml` is reserved for tools ([PEP 518](https://peps.python.org/pep-0518/#tool-table)).
- **ForgeGraph's case:** walk up from the *GraphSpec file*, as Ruff does, not from the current directory. Then the result doesn't depend on where the command was run, which matters for scheduled renders.

**Precedence and merging.**
- **git:** reads system, then global, then local, then worktree; "the last value found" wins. `-c` and `GIT_CONFIG_*` sit above the files ([git-config](https://git-scm.com/docs/git-config)).
- **pip:** reads Global, User, Site, then `PIP_CONFIG_FILE`. Command line beats env vars, which beat files; `PIP_CONFIG_FILE=os.devnull` turns all files off ([pip](https://pip.pypa.io/en/stable/topics/configuration/)).
- **uv:** project beats user beats system; arrays are concatenated; env vars and flags beat files; `--no-config` and `--config-file` exist ([uv](https://docs.astral.sh/uv/concepts/configuration-files/)).
- **Black:** the user file is used *only* when no project config exists, with no merging ([Black](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html)).
- **matplotlib:** runtime rcParams beat style sheets, which beat matplotlibrc, and the first matplotlibrc found wins ([docs](https://matplotlib.org/stable/users/explain/customizing.html)).

**Showing where a value came from.**
- `git config --show-origin` and `--show-scope` add the file path and the scope to every value ([git-config](https://git-scm.com/docs/git-config)).
- `ruff check --show-settings` shows the settings Ruff will use for a file ([Ruff](https://docs.astral.sh/ruff/configuration/)).
- `black --verbose` prints "Using configuration from …" ([Black](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html)).
- `pip config debug` lists the config files it consults ([pip](https://pip.pypa.io/en/stable/topics/configuration/)).
- matplotlib only reports which rc file was loaded (`matplotlib_fname()`) and keeps no per-key origin ([docs](https://matplotlib.org/stable/users/explain/customizing.html)).
- **The model for ForgeGraph is git's `--show-origin` plus `--show-scope`**, which D3 already cites: every value gets a file path and a layer.

## 3. Namespacing

| System | Form | Who picks the prefix | Collisions |
| --- | --- | --- | --- |
| npm scopes | `@scope/name` | the registry: only members can publish to a scope, so "you don't have to worry about someone taking your package name" ([npm](https://docs.npmjs.com/cli/v10/using-npm/scope)) | prevented by the registry |
| ESLint | `namespace/rule-name`, where the namespace is the key in `plugins`. By convention it's the package name without `eslint-plugin-`, but the user may rename it (`jsd/…`) ([ESLint](https://eslint.org/docs/latest/use/configure/plugins)) | the user | the user renames |
| Docker | `[HOST[:PORT]/]NAMESPACE/REPOSITORY[:TAG]`; the default host is `docker.io` and the default namespace `library` ([Docker](https://docs.docker.com/reference/cli/docker/image/tag/)) | the registry | prevented by the registry; bare names map to an official default namespace |
| Quarto | `<org>/<name>` on install; a format is referenced as `<extension>-<base>` (`acm-pdf`) ([managing](https://quarto.org/docs/extensions/managing.html), [formats](https://quarto.org/docs/extensions/formats.html)) | the GitHub org | not documented |
| VS Code | `${publisher}.${name}` ([manifest](https://code.visualstudio.com/api/references/extension-manifest)) | the marketplace | prevented by the marketplace |
| matplotlib | `package.style` (dotted) ([docs](https://matplotlib.org/stable/users/explain/customizing.html)) | the Python import name | first on `sys.path` wins |
| Hugo | no namespace: project first, then themes left to right, and "the left-most … will win" ([Hugo](https://gohugo.io/hugo-modules/theme-components/)) | n/a | silent precedence |
| Plotly | flat registry `pio.templates`; combined with `+` (`"plotly+draft"`) ([Plotly](https://plotly.com/python/templates/)) | n/a | last registration wins |

**What this means for ForgeGraph.**
- **Use `/`.** It's the npm, ESLint, Docker and Quarto convention, and the form D4 already uses (`acme/polarization-curve`). A `.` would clash with ForgeGraph's dotted parameter paths (`axis.tick.label.size`), and a `:` has no precedent among these tools.
- **PyPI has no scopes**, so two pip packs can declare the same entry-point name; the spec leaves that to the host. Following "error, don't fall back", two packs with one name should be an error naming both distributions, not Hugo-style silent precedence.

## 4. Style data packages: which one ForgeGraph resembles

| Package type | Manifest | Fields of interest |
| --- | --- | --- |
| Quarto extension | `_extension.yml`: `title`, `author`, `version`, `quarto-required: ">=1.2.222"`, `contributes: formats: …` ([Quarto](https://quarto.org/docs/extensions/formats.html)) | version requirement; contributions grouped by kind |
| VS Code extension | `package.json`: `engines.vscode` (versions it's compatible with, no wildcard), `contributes` ([VS Code](https://code.visualstudio.com/api/references/extension-manifest)) | version requirement; contributions |
| napari npe2 | `napari.yaml`: `name` (must match the package), `display_name`, `schema_version`, `contributions`; version and licence come from package metadata ([napari](https://napari.org/stable/plugins/technical_references/manifest.html)) | reuses pip metadata rather than duplicating it |
| Sphinx theme | `theme.toml`: `[theme] inherit, stylesheets, sidebars, pygments_style`, `[options]` with defaults ([Sphinx](https://www.sphinx-doc.org/en/master/development/html_themes/index.html)) | `inherit` is like ForgeGraph's `extends`; options with defaults are like `variable_parameters` |
| Hugo theme | folder layout by convention plus `theme.toml` metadata ([Hugo](https://gohugo.io/hugo-modules/theme-components/)) | contents found by folder convention |
| matplotlib style | a single `.mplstyle` file, no manifest ([docs](https://matplotlib.org/stable/users/explain/customizing.html)) | — |
| vega-themes | JS config objects in an npm package, chosen through vega-embed's `theme` option; no manifest beyond `package.json` ([vega-themes](https://github.com/vega/vega-themes)) | — |
| Plotly templates | Python objects in a registry ([Plotly](https://plotly.com/python/templates/)) | — |
| JupyterLab themes | prebuilt extensions in `share/jupyter/labextensions`, `install.json` ([JupyterLab](https://jupyterlab.readthedocs.io/en/stable/extension/extension_dev.html)) | — |

**Closest fit: Quarto's `_extension.yml` combined with npe2's discovery.**
- A Quarto extension is a folder with a small YAML manifest, a version requirement and contributions of named kinds, and Quarto even calls them "formats".
- npe2 shows how to ship such a folder in a pip package and find it without importing.
- From Hugo and ForgeGraph's own built-in layout, take the idea of finding contents **by folder convention** (`themes/`, `formats/`, `graphspecs/`, `catalogs/`, `references/`, `fonts/`) rather than listing them in the manifest. That keeps to "one source per fact".

**Recommended `pack.yaml` fields** (minimal):

| Field | Purpose |
| --- | --- |
| `name` | The namespace. Must match the entry-point name, and the folder name for a folder pack, as npe2 requires `name` to match the package |
| `version` | The pack's release version (PEP 440 or semver text). For pip packs it must equal the distribution version, or is read from it |
| `description` | One line, shown in `catalog` and `reference` |
| `requires` | A ForgeGraph version specifier (PEP 440, e.g. `">=0.6,<1"`), checked with `packaging`. A pip pack also declares it as a normal dependency |
| `suggested.theme`, `suggested.format` | Fully qualified names, applied when the pack is listed |

Don't add a `contents` list, or author and licence fields, which pip metadata already holds for pip packs.

## 5. Reference notes for agents

| Convention | Shape | Selection |
| --- | --- | --- |
| [AGENTS.md](https://agents.md/) | plain Markdown, no required fields; the nearest file wins; stewarded by the Agentic AI Foundation (Linux Foundation) | by directory |
| [llms.txt](https://llmstxt.org/) (Jeremy Howard, 3 Sep 2024) | Markdown: H1 name, blockquote summary, H2 sections of links, an "Optional" section an agent may skip | an index pointing to `.md` pages |
| [Agent Skills spec](https://agentskills.io/specification) | `SKILL.md` frontmatter (`name`, `description`), an optional `references/` folder "agents can read when needed", progressive disclosure (metadata, then body under 5000 tokens, then resources on demand), "Keep individual reference files focused", references one level deep | the agent picks by description |
| [Cursor rules](https://cursor.com/docs/context/rules) | `.cursor/rules/*.mdc` with frontmatter `description`, `globs`, `alwaysApply`; "Apply Intelligently" picks a rule by its description | by description, glob or always |
| [CLAUDE.md](https://docs.claude.com/en/docs/claude-code/memory) | plain Markdown memory files, with `@path` imports | always loaded |

**Recommendation.**
- **Format:** a pack's `references/*.md` are plain Markdown, each with a short YAML frontmatter `description:`, as SKILL.md and Cursor rules have. The file name is the note's name.
- **Size:** keep each note focused and under about 5000 tokens, the Agent Skills guidance.
- **`forgegraph reference`**, which follows progressive disclosure:
  - with no argument, it lists every active pack's notes as `acme/house: <description>`, an index like llms.txt;
  - `forgegraph reference acme` prints all of one pack's notes;
  - `forgegraph reference acme/house` prints one note.
- **Framing:** each printed note starts with a line naming its pack, version and file, saying it is reference material from that pack and not instructions (OWASP's "clearly denote"). `--json` gives `{pack, version, name, description, path, text}`.
- **Skill:** SKILL.md says to run `forgegraph reference` when a pack is active and to treat the notes as conventions, not commands. No edits to the skill per pack.

## 6. Recommended design

**Pack layout** (folder pack, or the package directory of a pip pack):
```
acme/
├── pack.yaml
├── themes/acme.yaml
├── formats/acme-slide.yaml
├── graphspecs/polarization-curve.yaml   # presets: GraphSpecs that others extend
├── catalogs/themes/acme.yaml            # catalog files, as for built-ins
├── references/house.md
└── fonts/*.ttf                          # registered with matplotlib's fontManager.addfont
```

**`pack.yaml`**, in the house definition-file layout:
```yaml
name: acme          # [text]; The pack's name, used as its namespace (acme/…). Must match the entry point or folder name.
version: 1.2.0          # [text]; The pack's release version.
description: Example organisation pack with a deliberately different house style.          # [text]; One line.
requires: ">=0.6,<1"          # [version specifier]; ForgeGraph versions the pack works with.
suggested:          # Applied when a config lists the pack and sets no value itself.
    theme: acme/acme          # [None, theme]; Suggested default theme. None: none.
    format: acme/acme-slide          # [None, format]; Suggested default format. None: none.
```

**Pip pack**, `pyproject.toml` (hatchling includes non-Python files in the package by default, subject to VCS ignores ([Hatch](https://hatch.pypa.io/latest/config/build/))):
```toml
[project]
name = "acme-forgegraph"
version = "1.2.0"
dependencies = ["forgegraph>=0.6,<1"]
[project.entry-points."forgegraph.packs"]
acme = "acme_forgegraph"      # a top-level package name, no ":attr"
```

**Discovery** (packs/):
1. Read `entry_points(group="forgegraph.packs")`.
2. For each entry point, reject an `attr` or a dotted module, since a dotted name makes `find_spec` import the parent. Call `importlib.util.find_spec(ep.module)`, take `submodule_search_locations[0]` and read `pack.yaml` there, as npe2 does.
3. Never call `ep.load()` or `importlib.resources.files(name)`.
4. Errors: a missing `pack.yaml`, a `name` that differs from the entry-point name, an unmet `requires`, or two packs with one name (name both distributions).
5. Folder packs are paths listed in config, resolved relative to the config file, as Ruff does.

**Config files** (TOML, as D4 says; parsed with stdlib `tomllib`):
- **User:** `$XDG_CONFIG_HOME/forgegraph/config.toml` (default `~/.config/forgegraph/config.toml`) on macOS and Linux; `%APPDATA%\forgegraph\config.toml` on Windows. `FORGEGRAPH_CONFIG=<file>` replaces it, and `FORGEGRAPH_CONFIG=` set empty, or `os.devnull`, means none, as pip does. Tests need this.
- **Project:** `forgegraph.toml`, found by walking up from the GraphSpec's folder. Its folder becomes the project root, which also holds the project's `themes/`, `formats/` and `graphspecs/`. With no `forgegraph.toml`, today's rule applies.

```toml
packs = ["acme", "../house-pack"]   # pip pack names or folder paths
theme = "acme/acme"                  # optional; overrides suggestions
format = "acme/acme-slide"           # optional
```
Three keys. No sections.

**Resolution of the theme and format choice**, highest first:
1. CLI flag (`render --format`);
2. the GraphSpec itself;
3. its `extends` chain;
4. project config;
5. user config;
6. `suggested` of a listed pack;
7. built-in `default`.

If two listed packs suggest different values and no config sets one, that is an error naming both. Parameter resolution inside the chosen files is unchanged: the nearest file wins, as in D3.

**Names.**
- Built-in items have bare names (`default`). A pack's items are `pack/name`, written the same way everywhere, including `extends` inside the pack's own files. Project-local items have bare names.
- A bare project name that equals a built-in name is an error, not a silent override.
- A name that doesn't exist suggests the nearest match, as `_suggest` already does.

**`forgegraph explain` shows:**
- the config files consulted, each marked found or not found (as `pip config debug` does);
- the packs found, with name, version, source (distribution or folder) and path;
- where `specifications.theme` and `specifications.format` were decided, e.g. `= acme/acme  (project config /p/forgegraph.toml)`;
- each value's origin, with its layer and path, e.g. `(fixed, theme 'acme/acme' — pack acme 1.2.0, …/themes/acme.yaml)`.

In `--json`, add `layer` and `file` to each row, alongside `set_by`.

**Keep minimal:**
- no system-level config;
- no `[tool.forgegraph]` at first;
- no fetching or caching of packs (pip does it);
- no `contents` list in `pack.yaml`;
- no precedence between packs (namespaces make it unnecessary);
- no user-level themes folder (a user makes a folder pack instead);
- no new `forgegraph config` command: `explain` and `catalog packs` cover it.

## 7. Open questions for the owner

1. **Are installed pip packs available unlisted?** One option is that they're usable by namespaced name as soon as they're installed, as matplotlib package styles are, with `packs = […]` needed only for folder packs and for suggested defaults. The other is that only listed packs exist, as with Sphinx and ESLint (D4 currently says "listed").
2. **User and project config: merge per key, or ignore the user file when a project config exists?** Merging per key is what git, uv and pip do. Ignoring the user file is what Black and Ruff do: more reproducible, because a teammate's user config can't change the project's graphs.
3. **Shadowing built-ins:** is a project file named like a built-in (`default`) an error, as recommended, or an allowed override? Today it silently overrides.
4. **Config format:** TOML, as D4 says (standard for tool config, `tomllib` in the standard library), or YAML in the house definition-file layout, which Phase 6 says to use "in the same layout as the others"? Likewise, does `pack.yaml` use the full header with `fixed_parameters` and `variable_parameters`, or the short form above?
5. **`version` field:** in `pack.yaml` it is the pack's release version (text), not the `[int]` specification version the other kinds use. Rename one of them, or accept that they differ?
6. **Separator and shorthand:** `acme/name` everywhere, or also let a bare `acme` mean the pack's suggested theme (like Docker's `library/`)? Recommended: no shorthand.
7. **Project root:** is it only the nearest `forgegraph.toml` walking up from the GraphSpec? Also stop at `.git`, as Black does? Also accept `[tool.forgegraph]` in `pyproject.toml`?
8. **Should the skill always write `theme` and `format` explicitly in GraphSpecs it saves**, so they render the same on another machine whatever its config? Recommended.
9. **Pack fonts:** may a pack's font share a family name with an installed font (which one wins), or is that an error?
10. **Should the private company pack be a pip package (git URL) or a folder?** This affects how it is pinned (lockfile or git commit) and how the trial is set up.
