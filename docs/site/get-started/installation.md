# Installation

ForgeGraph needs Python 3.12 or later.

```bash
pip install forgegraph
```

For the `forgegraph` command on its own, `uv tool install forgegraph` works too.

`forgegraph --version` shows the version you have. The first command that reads the configs, such as `forgegraph catalog`, writes the main config, `~/.config/forgegraph/config.toml`, listing the built-in packs.

To use ForgeGraph from an agent, install [the agent skill](skill.md) too.
