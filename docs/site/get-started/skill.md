# The agent skill

The skill lets an agent make and revise graphs with ForgeGraph: it takes the agent from your data to a finished graph, saving the GraphSpec beside it. To install it for Claude Code:

```bash
forgegraph skill install
```

For another agent, give the folder it reads skills from:

```bash
forgegraph skill install --dest <skills folder>
```

Then ask your agent for a graph. It chooses a graph type, theme, format and layers, writes the GraphSpec, renders it, and checks the lint and the image, revising until the graph meets your request. It uses the commands' `--json` output, and keeps to the packs your configs allow.

When ForgeGraph can't draw what you asked for, the agent says so and offers to file a feature request. It can also file bug reports for you, at [GitHub issues](https://github.com/sskaye/forgegraph/issues), or at the address a custom pack gives.
