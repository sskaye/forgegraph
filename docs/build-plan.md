# ForgeGraph — Build Plan

**Status:** Approved 2026-10-17 · **Implements:** [architecture.md](architecture.md) · **Author:** Claude (with Steven Kaye)

This plan turns the architecture into a sequence of phases. Each phase says what gets built, how it is tested and validated, and what, if anything, comes to you for review.

---

## 1. How the plan works

### 1.1 Gates

Every phase ends at a gate. Work on the next phase starts only after the gate is passed, unless the phase says otherwise.

| Gate | What happens |
| --- | --- |
| 🔍 **Review** | I deliver something for you to judge (a spec, a catalog, a demo). The next phase starts after you approve, or after your comments are addressed and you approve. |
| 📋 **Check-in** | I post a short phase report. You can skim it and raise concerns, but I don't wait for approval. |
| ✅ **Automatic** | CI and my own validation only. The report is in the PR. |

Review gates sit where judgement matters: document formats, how graphs look, how the skill behaves, and anything that runs on your real data. Mechanical phases get check-ins.

Some phases also open with a short **spec review**: a new specification file that phase needs (a further kind, such as layers or layouts, or a new graph type) is written in the same layout as the phase 1 specifications, with a Markdown mirror to comment on, and reviewed before its code. It works like a review gate, but covers only that file.

### 1.2 One branch and one PR per phase

- Each phase is built on a branch `phase-NN-<name>` and lands on `main` through a pull request.
- The **PR description is the phase report**: what was built, how it was validated (with results), deviations from the architecture, known issues, and what the next phase starts with.
- The catalog is reviewed in place in `catalog/`. Other review deliverables are committed under `review/phase-NN/` and linked from the PR, so Forgemark comments are versioned with the code.
- At a review gate, the PR merges when you approve it. At other gates, I merge it once CI is green.

### 1.3 Keeping the work on track

- **The architecture is the reference.** When building shows that a decision needs to change, I log it in `docs/decisions.md` (what, why, alternatives). What happens next depends on the size of the change:
  - **Small changes** are noted in the phase report.
  - **Changes to anything you reviewed or approved** stop work until you agree.
- **Format specs are contracts, with one allowance.** Field-level details found during the build of phases 2–3 (a renamed field, a missing option) are logged and re-confirmed at the phase 3 gate rather than stopping work. Structural changes still stop work. After phase 3, every change to an approved format stops work until you agree.
- **`main` is always green.** Tests, lint and type checks pass. Generated code is up to date: CI regenerates it and compares the text exactly. The catalog is current: CI compares its recorded input hash.
- **I check before you see anything.** Before any gate I run the full suite and look at every new or changed image myself. Where relevant, I also run the skill evals. You should never be the first to see a broken graph.
- **The plan gets revisited after each milestone** (§3): a short update in this document if scope or order should change.

### 1.4 Data handling

- The confidential example PDFs stay local and are never committed.
- Example graphs are recreated from **synthetic data** that mimics their shape but is rescaled, with neutral labels, so no real performance figures are implied.
- **Deny-list:** words that must never be committed here; currently one term, your company's name. A pre-commit hook and a CI check refuse any commit containing it, and also block secrets such as passwords and API keys. The term is matched regardless of case and inside longer words, so domains, handles and repo names are caught too. The list is kept outside the repo: in a local file, and as a GitHub secret for CI.
- Trials on your real data (phases 4, 6 and 8) run on your machine. Any company-specific pack lives outside this repo.

---

## 2. Conventions set up in phase 0

| Area | Choice |
| --- | --- |
| Python | ≥ 3.12; developed on 3.12. Your shell's default `python3` is 3.8, so environments are managed by `uv` and the system Python is never touched |
| Packaging | `pyproject.toml`, hatchling build backend, `src/` layout, `uv` for environments and the lock file |
| Quality | `ruff` (lint + format), `pyright` (types), `pytest` + coverage. Target ≥ 90 % line coverage on the core (spec, data, render) |
| YAML | `ruamel.yaml` (YAML 1.2, keeps comments and key order) |
| Image tests | Two tiers. On the same platform, output must be pixel-identical; across platforms, within a tolerance. Baselines are rendered by a CI job on Linux and change only through that job, with the image diffs shown in the PR |
| CI (GitHub Actions) | Linux on Python 3.12–3.14 on every push. macOS and Windows on one Python version, only on merge to `main` or on demand, because on a private repo their minutes count heavily against the free quota (10× for macOS) |
| Fonts | One OFL font family, bundled as static TTF instances (Source Sans 3 is the starting candidate), so output is the same on every machine |
| Licence files | `LICENSE` (MIT), `TRADEMARKS.md` |

---

## 3. Phases at a glance

| # | Phase | Milestone | Gate | For you to review |
| --- | --- | --- | --- | --- |
| 0 | Project scaffolding | M1 Foundation | ✅ | — |
| 1 | Format specifications + technical spike | M1 | 🔍 | The four specifications (theme, format, xy, an example GraphSpec) in Forgemark |
| 2 | Rendering core + `xy` | M1 | 📋 | Data source spec (at the start); otherwise reviewed with phase 3 |
| 3 | Catalog + default look | M1 | 🔍 | `xy` catalog and recreated example graphs; tuning the default theme together |
| 4 | Skill v1 + lint | M2 Usable | 🔍 | The skill evals: results, graphs and proposals |
| 5 | `bar`, first layers, presets | M2 | 🔍 | `bar` and layer specs, and an axis ticks and categories proposal (at the start); `bar` and layer catalog tabs; an ops-style graph from an Excel log |
| 7 | Layouts: multi-panel figures & dashboards | M3 Automation | 🔍 | Layout spec (at the start); a paper-style figure and an ops dashboard |
| 8 | Scheduling & freshness | M3 | 🔍 | A dashboard updating daily for a week (runs alongside phase 9) |
| 9 | Annotations, non-standard graphs, requests | M3 | 🔍 | Annotation catalog; one request filed end to end |
| 6 | Packs, config + a pack trial | M3 | 🔍 | Packs spec (at the start); then a trial of the skill with the forgegraph_base_2 pack |
| 10 | First public release (0.x) | M4 Release | 🔍 | Go/no-go on making the repo public + PyPI |
| 11 | `distribution` chart, iso-curves, `fit` → 1.0 | M4 | 🔍 | New catalog tabs; go/no-go on 1.0 |
| 12 | Studio desktop app | M5 Studio | 🔍 | UI plan; then a hands-on trial |

Phases run in the order listed: 7, 8 and 9 come before 6, so ForgeGraph is feature complete before packs. Each milestone ends with a plan revisit (§1.3).

---

## 4. Phase details

### Phase 0 — Project scaffolding · ✅ Automatic

**I will:**

- create the package skeleton (`src/forgegraph/` with the module layout in architecture §6), `pyproject.toml`, the `uv` lock file and the `forgegraph` entry point;
- add CI, pre-commit, `LICENSE` (MIT), `TRADEMARKS.md` and `docs/decisions.md`;
- bundle the fonts with their licence file;
- add the secret and deny-list checks;
- publish a minimal `0.0.1` to PyPI to hold the name, through GitHub's trusted publishing. It makes the name publicly visible, with an "early development" description and no code. You create the PyPI account and link it to the repo; I can't create accounts or handle tokens;
- add a `CONTRIBUTING.md` stub;
- record an initial search for existing "ForgeGraph" trademarks and products in the phase report.

**Testing and validation:**

- `uv sync` and `forgegraph --version` work on a clean checkout.
- CI is green on all three operating systems.
- A smoke test renders a figure containing text in the bundled font, and the output is pixel-identical across repeated runs on the same platform.
- The deny-list hook rejects a test commit containing a listed term.

**Deliverable:** none. One action for you: create the PyPI account and link it to the repo, so the placeholder can publish.

---

### Phase 1 — Format specifications + technical spike · 🔍 Review

**I will:**

1. **Run a throwaway technical spike first.** It renders one `xy` graph with direct labels, theme-to-matplotlib settings with isolation from user settings, and PNG/SVG/PDF with embedded provenance and TrueType fonts. It also builds a three-image catalog tab and rebuilds it with Forgemark comments in place, which settles how the build and CI call Forgemark's command-line tool (an installed package or a vendored copy). The aim is to test the risky technical assumptions before the specs commit to them. The spike code is not merged.
2. **Write the four specifications** (architecture §8): src/forgegraph/themes/default.yaml, formats/default.yaml, graph_types/xy.yaml and graphspecs/polarization.yaml, an example graph that sets every parameter. Each lists every parameter of its kind under fixed\_parameters or variable\_parameters, by category, with its value and a comment `[RANGE]; DESCRIPTION`.
3. **Write code that conforms to them.** It reads every parameter's definition, range included, from the default files, and checks and resolves any file of a kind against them: header, extends, fixed and variable, graph-type headings in themes and formats, and a GraphSpec's changes to its graph type, theme and format.

**Testing and validation (before you see it):**

- Every default file is valid, lists its header exactly, steps by four spaces, and every default value is within its range.
- For every parameter of every kind: both ends of each number range are accepted and values just outside are rejected; whole-number ranges reject fractions; every listed value is accepted and others rejected; type words, lists and single values are checked.
- Inheritance, graph-type headings, a GraphSpec's overrides (variable accepted, fixed refused), and every error message are tested.
- Spike findings are listed in the phase report, with any decisions they drove.

**Deliverable:** the four default files and the code and tests that conform to them. Later phases extend the specification by writing further files of each kind.

**Gate:** your approval. Field-level details may still be refined until the phase 3 gate (§1.3).

---

### Phase 2 — Rendering core + `xy` · 📋 Check-in

**I will build:**

- `resolve` with origin tracking, on top of the phase 1 specification code, and `forgegraph explain`;
- the **data source spec**, a fifth kind written and reviewed at the start of the phase: csv, tsv, tab, xlsx and xls files with sheet, header row, rows to skip and encoding (with fallback). A GraphSpec names a data source the way it names its theme; a graph can also be drawn from a DataFrame it's given. Plus its loader and `forgegraph inspect`;
- rendering from the default theme and format, and the label markup (D8);
- the rendering engine: isolated from user settings, drawing into a given Axes, never using `pyplot`;
- the `xy` graph type end to end, covering every row marked phase 2 in architecture §5. **Direct labels are a named sub-deliverable** with their own fixtures: crossing curves, converging ends, 10+ series, and the narrow paper format. The text-overlap check from lint is built here as their test oracle.
- export to PNG, SVG and PDF with provenance, recoverable via `fg.load` and `forgegraph load`, plus `--snapshot`;
- the Python API (`fg.xy`, `fg.render`, `Graph` with notebook display and escape-hatch detection) and the CLI (`render`, `inspect`, `explain`, `load`, `schema`, all with `--json`).

**Testing and validation:**

- **Unit tests:**
  - resolution order, merge rules and origins;
  - the data source loader against fixture files (messy Excel: header offsets, multiple sheets; a Windows-1252 CSV);
  - label-markup test vectors (including column names with underscores and `$`);
  - the provenance round trip for every file type.
- **Contract and perturbation tests** for `xy` (architecture §7), asserting on the figure's artists where possible.
- **Hostile-style test**, plus a test that layouts can place `xy` in a 1×2 grid.
- **PDF font test.**
- **Image regression** on a baseline set.
- **Recreation set:** about 8 of the example graphs rebuilt from rescaled synthetic data, e.g. polarization curves with a benchmark, the 6 vs 130 cm² colour × style pairing, replicates per group, the log-log precipitation plot, and the numeric colourbar scatter. I compare each one by eye against the original before reporting.

**Deliverable:** none. The recreation set (`review/phase-02/recreations.html`) and a short notebook showing the Python API are reviewed together with the phase 3 catalog.

---

### Phase 3 — Catalog + default look · 🔍 Review

**I will build:**

- `forgegraph catalog build`: the specification files → tabbed HTML catalog with parameter tables, the baseline example, and one image per variable parameter. Tabs cover graph types and the default theme and format; layer and preset tabs follow with those specs. Images are embedded at screen resolution.
- Stable ids down to individual table rows. The build carries the comment block over and re-attaches comments by anchor text using Forgemark's `reattach`, then runs `forgemark lint`.
- The catalog's recorded input hash, plus a CI check that it matches the current definitions.
- A small **visual-changelog** script: before and after images of every gallery example whose baseline changed between two commits.

**Testing and validation:**

- Building twice gives identical HTML.
- **Forgemark round trip:** a fixture with comments made in the Forgemark app, on prose and on table cells. After a rebuild with unchanged text, the test asserts zero orphans. This runs in CI.

**Deliverable:** the **`xy` catalog** for review in Forgemark, in place in `catalog/`, together with the phase 2 recreation set and API notebook. This is also where we tune the **default look** together: you comment on the gallery, I adjust the theme, the catalog rebuilds with your comments still attached, and we repeat until you're happy. Field-level spec refinements from phases 2–3 are listed for your confirmation.

**Gate:** approval of `xy`, the default theme, and the spec refinements. After this, theme changes appear in the visual changelog.

---

### Phase 4 — Skill v1 + lint · 🔍 Review

**I will build:**

- `SKILL.md` and example GraphSpecs, shipped inside the package and installed with `forgegraph skill install`. Version-dependent content is fetched at run time from `forgegraph catalog` and `forgegraph schema`.
- The render → look → lint loop.
- **Lint v1:** overlapping or clipped text, legend over data, too many categories for the palette, non-positive values on a log axis, points outside fixed limits, fonts too small for the format, font fallback, and dropped rows.
- **Behaviour for unsupported requests:** until phase 9, the skill says plainly that a graph type isn't supported yet and offers the closest supported graph, without drawing it another way.
- **The input contract:** ForgeGraph draws a pandas DataFrame, passed through the Python API or read from the Parquet file a GraphSpec's `data.file` names, with an optional `data.preprocessing` reference recorded in provenance (architecture D7). The skill starts from that DataFrame.

**Testing and validation:**

- **Lint tests:** a deliberately bad figure for each check, plus a clean one.
- **Skill evals:** 20 requests over the sample datasets, written as expert users write them and reviewed by you (review/phase-04/skill-evals.md). They cover scatters and lines of groups, dates, log axes, missing values, messy Excel and CSV files, multi-turn edits of one GraphSpec, theme rules, and unsupported requests.
  - **Grading:** each is graded automatically on the GraphSpec's values and data, a clean lint, the files made, whether the agent looked at the image, and what it says about unsupported requests. I also look at every graph.
  - **Runs:** each case runs once on each of Opus, Sonnet and Haiku, locally through Claude Code, with no API key and no separate API charges.

**Deliverable:** the eval results, with every graph, and proposals for what they show (review/phase-04/skill-eval-results.md).

**Gate:** you approve, or list what feels wrong, which becomes new eval cases before fixes.

---

### Phase 5 — `bar`, first layers, presets · 🔍 Review

**I will build:**

- **spec review at the start:** the `bar` graph type's file, and the **layer spec**, a further kind for things drawn on the graph: reference lines (fixed, or at a statistic such as the mean), notes and error bars;
- **a proposal at the start, for your review:** axis ticks and categories: setting where ticks go and how values are labelled (months 1–12 as Jan–Dec, say), and text categories along an axis, with as few new parameters as possible;
- the `bar` graph type (vertical/horizontal, grouped/stacked, error bars, direct value labels);
- the `reference_line`, `note` and `error_bar` layers; error bars are drawn from error columns in the DataFrame;
- the built-in `scatter` and `line` presets: GraphSpecs that other GraphSpecs extend;
- updates to the skill and evals for bars and layers.

**Testing and validation:**

- `bar` gets contract, perturbation and image tests like `xy`; the layers are tested on both graph types.
- New skill evals: "weekly count of completed runs by instrument from this log", "mean ± SEM per condition", with the agent preparing the DataFrame.

**Deliverable:**

- the `bar`, `reference_line` and `note` catalog tabs in Forgemark;
- an **ops-style graph** (weekly throughput from a synthetic Excel lab log) made through the skill, which you can then repeat with a real log.

---

### Phase 6 — Packs, config + real-data trial · 🔍 Review

**Spec review at the start:** the pack and config specs (docs/specs/pack, docs/specs/config), the `acme` example pack and the base specs' names, all reviewed (architecture D4).

**I will then build:**

- packs as the only source of named specs: folder packs, and pip packs found through package metadata without importing them;
- the built-in pack `forgegraph_base`, its specs renamed `base_theme`, `base_format`, `base_layout_format`, `base_layout` and `base_schedule`;
- the main and folder configs, a pack only a folder config lists working but non-standard, each misconfiguration an error naming its files;
- GraphSpecs that name their graph type, theme and format, and layouts their format, with nothing supplied when one is missing;
- `forgegraph catalog` listing the allowed packs' specs, `forgegraph explain` naming each value's pack, and `forgegraph pack-notes`;
- the `acme` example pack, in a deliberately different style, with a theme, format, GraphSpec, layout and schedule.

**Testing and validation:**

- **Resolution tests:** names across packs and `extends`, and the main and folder configs combined, including every case's error.
- The whole gallery renders under `acme`.
- Skill evals run with `acme` allowed.
- Layouts and schedules naming pack specs (`acme/slide`) resolve, and the watermark test covers pack themes.

**Deliverable: a trial with the forgegraph_base_2 pack.**

- **Trial:** you follow the runbook (review/phase-06/runbook/README.md) with its sample data: the skill with the pack allowed, not allowed, and listed only in a folder config.
- **Follow-up:** fixes come with regression tests, and a short findings list records what was fixed and what's deferred.

**Gate:** your go-ahead from the trial. Then the milestone plan revisit. The trial on your company's data comes after the public release (see After the first release).

---

### Phase 7 — Layouts · 🔍 Review

**Spec review at the start:** the layout spec, a further kind (a format, separators, and tabs of GraphSpecs on a grid). Each tile is a GraphSpec drawn from its `data.file`.

**I will then build:**

- layouts: each tab one matplotlib figure, its tiles' plot boxes aligned on the grid, with the separators between them;
- PNG, PDF and HTML output for layouts (a file per tab, a page per tab, one page with a tab bar), and HTML output for GraphSpecs (the figure as SVG in a minimal page);
- updates to the skill.

**Testing and validation:**

- Image tests for multi-panel figures: alignment across tiles with different tick-label widths, spans, blank cells, separators, tiles in different themes.
- HTML page tests.
- Recreations of the side-by-side example slides from rescaled synthetic data. Only panels whose graph types already exist are included (Ex1 p3, Ex2 p7); panels that need the `distribution` chart, iso-curves or fits are completed in phase 11.

**Deliverable:** a **paper-style multi-panel figure** and an **ops dashboard**, for you to judge whether the layout formats the way you want (a concern you raised during review). Each is made from the sample data in the repository and from your company's data, kept outside it, so real data is tried before phase 8.

---

### Phase 8 — Scheduling & freshness · 🔍 Review

**Spec review at the start:** the schedule spec, a further kind (targets, cadence, freshness, the status file, `on_failure` and `on_success`). A scheduled job renders GraphSpecs and layouts; keeping their Parquet files current is the user's job.

**I will then:**

- build `forgegraph job run`, which runs a schedule once; whatever the environment offers schedules it.
- add the status file, the `on_failure` and `on_success` hooks, the in-image "data as of" footnote (the data files' modification time) and the HTML stale banner;
- add a skill step for scheduling a job, and an example schedule.

**Testing and validation:**

- Unit tests for scheduling and status.
- A simulated clock test for the stale banner.
- A failure-injection test: when a GraphSpec's data file disappears, the status file records the error, `on_failure` fires, and the banner turns stale on schedule.

**Deliverable:** a **real dashboard updating daily for a week** on your machine, built from your data. You check it a couple of times during the week, and at the end I report on its runs and anything that went wrong. **The week runs after the public release** (see After the first release).

---

### Phase 9 — Non-standard graphs and requests · 🔍 Review

**I will build:**

- the escape hatch (`fg.blank`, themed helpers) and the always-on watermark, including outputs edited after rendering;
- feature requests and bug reports: one line in the skill, pointing to a reference file that says where to send them.

**Testing and validation:**

- The watermark is present on every non-standard path, including escape-hatch edits, and no GraphSpec can remove it.

**Deliverable:** none of its own. Filing a real request through the skill is part of the trial on your company's data, after the public release.

---

### After the first release

- **The trial on your company's data:** I help you set up a **private pack** for your company outside this repo (reference notes, and a house theme if you want one); we run the skill together on your company's data, which the agent prepares in its own way and saves as Parquet; and you file one real request through the skill, to judge whether it's easy enough. Fixes come with regression tests, and a findings list records what was fixed and what's deferred.
- **Phase 8's week:** a real dashboard updating daily for a week on your machine, built from your data.

---

### Phase 10 — First public release (0.x) · 🔍 Review

**I will:**

- write the README (including the "your graphs are yours" statement) and the user docs;
- write CONTRIBUTING (and the CLA decision, if you've made one) and a CHANGELOG with the visual changelog;
- do a release dry run on TestPyPI;
- update the trademark search;
- scan the full git history for secrets and deny-listed terms;
- prepare both options for going public: flipping this repo to public, or publishing a fresh repo with squashed history, which leaves out internal review comments.

**Testing and validation:**

- Install from TestPyPI on a clean machine on each operating system.
- Run the skill evals against the installed package.
- Smoke-test the skill on a second agent (Codex) if it's available, since the spec lists Codex among the interfaces.

**Deliverable:** a **go/no-go decision** for you: which way to go public, and whether to publish 0.1 to PyPI. Nothing is published without your explicit yes.

---

### Phase 11 — `distribution` chart, iso-curves, `fit` → 1.0 · 🔍 Review

**I will build:**

- the `distribution` graph type (box + strip, categorical x);
- the `iso_curve` layer (x·y = c and similar);
- the `fit` layer, each with its definition reviewed as a proposal first;
- the side-by-side slide recreations deferred from phase 7.

**Testing and validation:** the standard contract, perturbation and image tests, plus recreations of Ex1 p3, Ex2 p1, p5 and p6.

**Deliverable:** the new catalog tabs, for review in Forgemark, and a go/no-go on releasing 1.0.

---

### Phase 12 — Studio desktop app · 🔍 Review

**I will:** build Studio per architecture D14:

- opening a GraphSpec, or a Parquet file to start a new one; fields panel, shelves that map the DataFrame's columns to X, Y, color, style and series, options panel generated from the schema, and live preview;
- the theme and format editor;
- opening specs and PNGs;
- packaging as a desktop app.

The phase starts with a short **UI plan and click-through mockups**, including the choice of UI framework. You review them before the app is built.

**Testing and validation:**

- Shelf round-trip tests across all catalog examples.
- End-to-end UI tests for the main flows.
- Performance: preview under 0.5 s for typical graphs.

**Deliverable:** a **hands-on trial**: you make several graphs without an AI and judge whether Studio is enough.

---

## 5. Not covered by this plan

- **Interactive output.** It's post-MVP and gets planned only if it becomes a requirement.
- **Deferred items** (architecture §11): the MCP server, KPI tiles, responsive dashboards, `forgegraph migrate`, further graph types. These are added through the request flow or a plan revisit.
- **Calendar dates.** Phases are sequenced, not scheduled. Pace depends on your review availability, and the gates are designed so nothing piles up unreviewed.

