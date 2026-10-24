# Phases 6 and 9: what to review

1. **The base pack's catalog,** [catalog/forgegraph_base.html](../../catalog/forgegraph_base.html): ForgeGraph's graph types and layer types, and forgegraph_base's base_theme, base_format and base_layout_format. The theme has four new parameters (font.weight, plot_area.line_color, series.line.cap and join, legend.key.background), each with its card.
2. **forgegraph_base_2,** the pack made from your tableau_like style: [packs/forgegraph_base_2](../../packs/forgegraph_base_2), its catalog [catalog/forgegraph_base_2.html](../../catalog/forgegraph_base_2.html), and a comparison with matplotlib's output for the same data, at the same scale: [forgegraph_base_2-vs-matplotlib.png](forgegraph_base_2-vs-matplotlib.png) (matplotlib left, ForgeGraph right). Renamed from boxed_sans.
3. **The acme example pack,** [examples/packs/acme](../../examples/packs/acme), allowed through a folder config (forgegraph.toml) in the tests and evals.
4. **The specs,** [docs/specs](../../docs/specs): the base specs under their new names, the pack and config specs, and the provenance spec.
5. **The skill,** [SKILL.md](../../src/forgegraph/skill/forgegraph/SKILL.md): two proposals from the evals, as comments.
6. **The eval results,** [review/phase-09/skill-eval-results.md](../phase-09/skill-eval-results.md): 186 runs, the graphs, and two proposals as comments.
7. **The forgegraph_base_2 pack trial,** [runbook](runbook/README.md): for you to run, with its sample data.
