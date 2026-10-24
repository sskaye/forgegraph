# Escape hatch, watermark and request flow: research for phase 9

Input for the phase 9 proposal. Sources are numbered [n] and listed at the end. "Probe" means I checked the claim against the current code by running a scratch script outside the repo.

## 0. What the current code does, and the gaps that matter for phase 9

- `Graph.nonstandard` compares the ids of the figure's child artists with a snapshot taken at the end of `render()` (src/forgegraph/graph.py, `_artists`). `mark()` adds the watermark, and `save()` and `_repr_png_()` call `mark()`. `ProvenanceRecord.nonstandard` records the flag (src/forgegraph/spec/provenance.py).
- **Gap 1: changes to existing artists go undetected.** Probe: `lines[0].set_color("red")`, `set_xlim(0, 100)`, `set_title("changed")` and changing an axis title's text all leave `nonstandard == False`. The output is saved unwatermarked, with a GraphSpec that no longer reproduces it.
- **Gap 2: `g.figure.savefig(...)` skips everything.** Probe: after `g.axes.plot(...)`, a direct `g.figure.savefig("x.png")` writes a file with no watermark and no ForgeGraph record.
- **Gap 3: a theme can hide the watermark.** Probe: a project theme extending `default` with `watermark: {opacity: 0.0, color: "#FFFFFF", span: 0.01, text: "."}` validates, renders and saves a non-standard graph with no visible mark. This contradicts D10's "a theme can restyle it but not remove it". The ranges in themes/default.yaml allow opacity 0 and span near 0, and any text.
- **Gap 4: whitespace watermark text crashes at save time** (`AttributeError: 'list' object has no attribute 'flags'` from the empty TextPath). Per the "error, don't fall back" rule, this should be a validation error naming `watermark.text`.
- **Gap 5: `provenance.level: off` drops the `nonstandard` flag** along with everything else. The watermark still shows, but the file can't be told apart from one with no ForgeGraph record.
- **D10 is out of date about `gh` and images.** GitHub CLI 2.99.0 (released 2026-09-01) added a repeatable `--attach` flag to `gh issue create`, `gh issue edit` and `gh issue comment`. It uploads images or video, and rewrites `![alt](./file.png)` references in the body to the uploaded URLs, on GitHub.com and Enterprise Cloud [1][2]. The machine here has gh 2.95.0, which doesn't have the flag.

## 1. How high-level plotting libraries hand over to the low-level one

| Library | Hand-over | What stays themed |
|---|---|---|
| seaborn | Axes-level functions return the matplotlib Axes; figure-level functions return a FacetGrid whose axes you draw on [3]. `sns.axes_style(...)` works as a context manager that "temporarily alter[s] the global defaults" [4] | Anything drawn inside the style context |
| plotnine | `ggplot.draw()` returns a matplotlib Figure [5] | Only what plotnine drew; later additions use the user's rcParams |
| Plotly | Express returns an ordinary `graph_objects.Figure`, changed afterwards with `update_layout`, `update_traces` or `add_trace` [6] | The template applies to new traces too, because it lives in the figure's layout |
| Vega-Lite | Compiles to Vega (`vl2vg`, `vegaLite.compile`) for things Vega-Lite can't express [7]. `usermeta` is a free-form metadata object that "is completely ignored by Vega and Vega-Lite" [8] | Nothing; the compiled Vega is raw |
| matplotlib | Style sheets, `plt.style.context(...)` and `rc_context(...)` scope rcParams to a block. Runtime rcParams beat style sheets, which beat matplotlibrc [9]. A `Figure` subclass passed as `FigureClass` changes figure behaviour; matplotlib's own example is a `WatermarkFigure` [10] | Everything inside the context |

What the established pattern suggests for a themed blank figure:

1. **A scoped style context** (the seaborn and matplotlib pattern) while the user's code draws, so new artists pick up the theme's fonts, line widths, colors and tick styling. ForgeGraph already has this as `isolated(style)`. The gap: code drawing on `g.axes` outside ForgeGraph's own calls doesn't run inside it today.
2. **Return the real matplotlib objects** (seaborn, plotnine, Plotly), not a wrapper API. This is what makes the escape hatch useful.
3. **Helpers for what rcParams can't express.** ForgeGraph's look depends on things outside rcParams: the extended Wilkinson tick algorithm, text trimmed to its letters, title and axis-title gaps, direct labels and the style key. Themed helpers expose these to hand-written code; Plotly's equivalent is that the template lives on the figure itself [6].
4. **A Figure subclass** is matplotlib's documented way to make a figure behave differently on every path, including `savefig`, `show` and notebooks [10]. It is the established place to put the watermark, so Gap 2 closes by construction.

## 2. Marking outputs edited after the library finished

**Inside the process (before saving).** No plotting library I found detects edits; ForgeGraph's need is unusual. The robust established technique is a content fingerprint: compare the rendered result, not the object graph. Recommendation:
- At the end of `render()`, keep (a) the artist-id tuple (cheap; catches additions) and (b) a SHA-256 of the Agg canvas's RGBA buffer, drawn without the watermark.
- At `save()`, `show` and draw time, check (a). Before saving, also redraw and compare (b). Any visible change sets `nonstandard`, which closes Gap 1. A change that leaves no pixel different doesn't matter for the output.

**After saving (the file itself is edited).** C2PA, as context only: a C2PA manifest carries a *hard binding*, "one or more cryptographic hashes that uniquely identifies either the entire asset or a portion thereof". The hashed byte range excludes the manifest's own bytes. If the hash doesn't match on validation, the manifest is rejected with `assertion.dataHash.mismatch`, because "it is unknown if that is because of (a) modification of the asset or (b) the wrong C2PA Manifest Store was located" [11]. C2PA adds *soft bindings* (invisible watermarks or fingerprints) only to *recover* a manifest after a platform strips metadata [12]. A recovered match is weaker than an exact signature [13].

Carrier conventions that apply:
- **PNG.** Predefined text keywords include Title, Author, Description, Software, Source and Comment, and `XML:com.adobe.xmp` for XMP in an iTXt chunk [14 §11.3.3.1]. ForgeGraph's custom "ForgeGraph" keyword is allowed. PNG editors "always [are] allowed to copy all unrecognized ancillary chunks if [they have] only added, deleted, modified, or reordered ancillary chunks" [14 §14.2]. In practice many editors and optimisers drop them, which is why D13 already treats metadata as strippable.
- **XMP Media Management** gives each file a DocumentID and an InstanceID that is "updated each time a file is saved", plus an `xmpMM:History` of stEvt actions with a software agent [15]. XMP-aware editors (Adobe, Inkscape) maintain these. A changed InstanceID is a second, weaker edit signal.
- **PDF 2.0** deprecates the Info dictionary in favour of the catalog's XMP metadata stream [16]. ForgeGraph writes `/ForgeGraph` in the Info dictionary through matplotlib, which still works. Moving to XMP is a later option, not a phase 9 need.

**Robustness limits (state these plainly in the docs):**
- Stripping metadata (PowerPoint and Slack, per D13) removes the record entirely. The established reading, which C2PA also uses, is that **a missing or invalid record is itself the signal**: the file isn't certified as a standard ForgeGraph graph. Absence proves nothing about intent.
- A hash without a signature shows accidental or naive edits, not forgery. Someone who edits the JSON can recompute the hash. Signing is C2PA's territory and should stay out of scope.
- No watermark can be added to a file edited in another program. For files edited after saving, ForgeGraph can only *report*, never *mark*.

**Recommended content hash (C2PA hard-binding pattern, no signature):**
- PNG and TIFF: SHA-256 of the decoded pixels (mode, size, bytes) via Pillow. This survives lossless re-encoding and metadata-only rewrites, and catches any pixel edit.
- SVG, PDF and JPEG: SHA-256 of the file bytes with the record's value excluded. Write the record with a fixed-length 64-hex placeholder, hash the file with that range treated as the placeholder, then patch the hash in place at the same length. Nothing moves, so PDF xref offsets stay valid. This is C2PA's exclusion-range approach.
- Store it as `content_sha256` in the record, at every provenance level except `off`.

## 3. Issue intake for feature requests

**GitHub issue forms** (YAML in `.github/ISSUE_TEMPLATE/*.yml`; public preview) [17][18]:
- Top-level keys: name and description (both required), body, title (pre-filled), labels, assignees, projects, type. Labels apply "if they already exist".
- Body elements: `markdown`, `input`, `textarea` (`render: <language>` turns the value into a code block and disables attachments), `dropdown` (`options`, `multiple`, `default`), `checkboxes` (per-option `required`), and `upload` (with `validations.accept` as a list of extensions).
- Upload limits: images (png, jpg, gif, svg, webp) up to 10 MB. Text (csv, json, py, txt…) up to 25 MB. **Parquet isn't an accepted type**, so sample data goes in as CSV.
- `validations.required` applies only in public repositories.
- `id` (alphanumerics, `-` and `_`, unique within the form) is "the canonical identifier for the field in URL query parameter prefills" [18]. So `issues/new?template=graph-type-request.yml&title=…&name=violin` can prefill single fields. A URL that is too long gets a 414 [19].
- `config.yml`: `blank_issues_enabled` and `contact_links` (name, url, about). Template names must be longer than 3 characters [20].
- A submitted form becomes Markdown with a `### <label>` heading per field and `_No response_` for empty ones (seen in pandas #71259). Actions such as `github-issue-parser` parse that layout into JSON keyed by field id [21].

**`gh` and forms:**
- `gh issue create` doesn't support issue forms (cli/cli#5865, open) [22]. `--template` only seeds Markdown templates, and the GraphQL `issueTemplates` query doesn't list `.yml` forms [23]. **An agent filing through `gh` bypasses the form**, so the helper must write the body in the form's exact `### label` layout. Then issues filed through `gh` and through the web look and parse the same.
- `--label` is silently dropped for users with Read access (cli/cli#13589) [23]. GitHub's GraphQL `createIssue` input has `issueTemplate`, which "assigns labels and assignees from the template to the issue" (schema introspection). A user reports this works with `.yml` forms for Read users [23]. Labels don't apply for most outside requesters through plain `gh issue create`. The robust key for finding requests is therefore the title prefix plus a hidden marker in the body, not a label.
- Useful commands:
  - `gh issue create --title … --body-file … --attach mock.png` [1]
  - `gh issue comment N --body-file … --attach …` [1]
  - `gh search issues --repo R --match title,body --state open|closed --sort reactions-+1 --json …`
  - `gh issue list -S '<query>'`
  - a 👍 reaction: `gh api -X POST repos/R/issues/N/reactions -f content=+1` [24]
  - search qualifiers such as `in:title`, `in:body`, `is:issue`, `reason:"not planned"` and `reactions:>n` [25]

**Examples from data-viz projects** (fetched from each repo's `.github/ISSUE_TEMPLATE`):
- matplotlib `feature_request.yml`: a form with title "[ENH]: ", label "New feature", a "please search the issues" note, Problem (required; the placeholder suggests "a sample image of what I am asking for") and Proposed solution. Its `config.yml` points questions to Discourse [26].
- pandas `feature_request.yaml`: labels [Enhancement, Needs Triage]. Feature Type checkboxes; Problem Description, Feature Description and Alternative Solutions, all required [27].
- plotly.py `feature_request.md`: Description, "Why should this feature be added?", **Mocks/Designs**. It asks for search first, says +1 comments "will be deleted", and asks for reactions instead [28].
- Vega-Lite `Enhancement.md`: asks for an example spec, and to "prototype multiple alternative syntaxes", plus an "I checked for duplicate issues" checkbox. `blank_issues_enabled: false` [29].
- ggplot2 `feature_request.md`: motivate the change "with a **minimal reproducible** example (reprex)". It also warns that new features which extensions can cover are unlikely to be accepted [30].

The common elements: search first; the problem before the solution; why existing features don't fit; a mock-up or image; a minimal example; reactions rather than "+1" comments.

## 4. Privacy: sample data that never leaks the real data

- **Established guidance.** Stack Overflow's MRE is "Minimal… Complete… Reproducible" [31]. reprex says to "use the smallest, simplest, most built-in data possible" and, failing that, to "minimize their size and complexity", with `set.seed()` for random data [32]. ggplot2 points requesters to reprex [30]. None of these sources addresses confidential data directly. Their implied rule is built-in or made-up data.
- **Synthetic data fitted to real data still leaks.** Tools like SDV judge privacy by whether synthetic rows copy real ones [33]. Published summary statistics alone can allow database reconstruction [34]. So "match the real ranges and distributions" is itself a disclosure.
- **What follows for ForgeGraph:**
  - The helper should **never read the user's data**. It takes only the *shape*: column roles from the draft graph type (for example x: category with k levels; y: number), a distribution family, a row count and a seed. From these it generates the values (numpy `default_rng(seed)` [35]).
  - Column names and category levels are **generic by default** (group A/B/C, value). Real names appear only when the user approves each one, because a column name can be confidential too.
  - The mock-up attached to the request is **re-rendered from the sample data** with the same drawing code. It is never the step-2 image, which shows real data.
  - The drawing code can still embed real strings or numbers (titles, annotation values, hard-coded limits). The helper can't detect those reliably, so the skill's review step (show everything before filing) remains the control. The helper can flag string and number literals in the code to make that review easier.

## 5. Maintainer triage

- **GitHub's own mechanisms:**
  - Default labels include duplicate, enhancement, invalid, question and wontfix. Write access creates labels; triage access applies them [36].
  - "Duplicate of #N" in a comment creates the duplicate timeline event (commenter needs write access) [37]. `gh issue close N --reason "not planned"|duplicate --duplicate-of M` (gh help) is the close-reason equivalent of the wontfix and duplicate labels.
  - Linked branches: `gh issue develop N --name proposal/<name>` creates a branch shown under the issue's Development section. A PR from it links to the issue automatically [38].
- **Label taxonomies in data-viz projects** (from `gh label list`):
  - matplotlib uses "status: needs clarification / duplicate / won't or can't fix" plus "New feature".
  - pandas uses "Needs Triage" (added by the form), "Needs Info", "Needs Discussion" and "Duplicate Report".
  - napari uses "triage:duplicate / not-planned / needs decision".
  - Vega-Lite uses "Duplicate", "Enhancement" and "Wontfix".
- **matplotlib's triage guide** [39]: thank the reporter; ask for missing information with "needs clarification" and close only after "at least a week"; point duplicates at the original, close them and label "status: duplicate", folding any new information into the original; fix the title; label. (It also says AI tools aren't appropriate for *resolving* good-first issues. That's a different activity from agent-assisted triage with maintainer approval.)

## 6. Recommended design

### 6.1 `fg.blank`

- `fg.blank(theme="default", format="default", *, name, rows=1, columns=1, registry=None) -> Graph`
  - It returns the existing `Graph`, with `.figure`, `.axes` (an array when there are several panels) and `.style`. `nonstandard` is fixed True, and `record()` gives `kind: blank`.
  - Used as a context manager, `with fg.blank(...) as g:`, the theme's rcParams apply while the user's code draws, like `plt.style.context` and `sns.axes_style`. On exit, ForgeGraph's own layout runs, then lint (`g.check()`). Outside the context, a `Graph` is still usable; drawing outside it just isn't themed.
- **Drawing code is a file, recorded as text, never run when a file is loaded.** `forgegraph draw <name>.draw.py --theme … --format … --data <parquet> [--out …]` runs a file defining `draw(g, data)`. It embeds the script's text in provenance as `code`, and the request helper reuses the same file. From Python, `g = fg.blank(...).draw(func, data)` records `inspect.getsource(func)`. This keeps D7's rule: rendering a shared GraphSpec never runs code, and `forgegraph load` only shows the code.
- **Themed helpers:** methods on the Graph where they need its layout, module functions otherwise.
  - `fg.palette(theme)` gives the resolved series.colors as hex; `fg.colormap(theme)`.
  - `g.title(text)` and `g.axis_titles(x=…, y=…)` use the theme's sizes, weights and letter-trimmed gaps.
  - `g.ticks(axis, scale="linear"|"log")` installs the theme's tick algorithm as a matplotlib Locator.
  - `g.key(handles, labels, title=None)` draws ForgeGraph's style key.
  - `fg.annotate.*` are the phase 9 annotation layers, usable on any Axes in data coordinates.
- `Figure` becomes a ForgeGraph `Figure` subclass [10]. Its `draw()` checks `nonstandard` and adds the watermark first, so `savefig`, `show`, notebooks and `g.save()` all get it.

### 6.2 Watermark rules

- **When:** every `fg.blank` output, and every rendered Graph whose fingerprint changed (artist ids, or the pixel hash before saving; see §2). Never on an unchanged catalog render.
- **What:**
  - The theme's `watermark.text` (default NON-STANDARD), centred on and fitted to each plot box. With several panels it is either one mark across the union of the panel boxes or one mark per panel (§7).
  - Provenance gets `nonstandard: true`, `kind: blank | edited`, `code` (blank only) and `content_sha256`.
  - Lint adds an issue that tells the user, in plain words, that the graph is non-standard and why.
- **Unremovable by a theme:** validation errors, not clamping, per the "error, don't fall back" rule.
  - `watermark.opacity` has a floor (for example ≥ 0.12).
  - `watermark.span` has a floor (for example ≥ 0.5).
  - `watermark.text` must contain at least one visible glyph, which also fixes Gap 4.
  - `watermark.color` must reach a contrast of at least 3:1 against `background.color`. That is WCAG's threshold for non-text graphics [40].
  - A test renders each built-in and pack theme with and without the mark and asserts a minimum share of changed pixels in the plot box.
- **`provenance.level: off` and non-standard output:** either the record shrinks to `{nonstandard: true, forgegraph: <version>}`, or the no-record rule stands (§7).
- **After saving:** `forgegraph load` (and a `verify` mode) reports one of four states:
  - standard and unedited;
  - non-standard (with its kind);
  - **edited after saving** (the record is present but the content hash doesn't match);
  - no ForgeGraph record.

  The skill runs it whenever the user supplies a graph file. For an edited file, or one without a record, the agent says so and works from the GraphSpec rather than the pixels.

### 6.3 `forgegraph request --draft <name>`

**Inputs:**
- the name;
- `--roles` (for example `x=category:3 y=number`);
- `--rows`, `--distribution` and `--seed`;
- `--draw <file>.draw.py` (optional);
- `--names` to rename generic columns with user-approved names;
- `--describe` and `--why` text from the agent.

It **takes no data path**. Passing a file is an error that explains the rule.

**It writes the folder `requests/<name>/`, containing:**
- `issue.md`: the body in the form's exact `### label` layout, plus a hidden marker `<!-- forgegraph-request v1 -->`.
- `comment.md`: the shorter version, for adding a use case to an existing issue.
- `graph_type.yaml`: a draft with `status: requested`, also shown in issue.md as readable tables, with the raw YAML in a collapsed `<details>` block.
- `sample.csv` and `sample.parquet`: generated data.
- `draw.py`: the drawing code, reading only sample.parquet.
- `mockup.png`: re-rendered from the sample data by draw.py, watermarked.
- `manifest.json`: generator, seed and roles, plus the list of literals found in draw.py for the user to review.

### 6.4 The "Graph type request" issue form

The form lives at `.github/ISSUE_TEMPLATE/graph-type-request.yml`, with the title "[Graph type]: " and the labels [graph type request, needs triage]. Fields in order:
1. markdown: search existing requests first; use made-up data only; no code needed.
2. input `name` (required): proposed graph type name.
3. textarea `purpose` (required): what the graph shows and the question it answers.
4. textarea `why_not_existing` (required): the closest existing types, layers or presets, and why they don't fit.
5. upload `example` (accept png, jpg, svg, pdf): example image, sketch or mock-up.
6. textarea `data_shape`: columns and their roles, types and made-up example values.
7. upload `sample_data` (accept csv): optional made-up sample data.
8. textarea `definition` (`render: yaml`): optional draft graph_type.yaml.
9. textarea `code` (`render: python`): optional matplotlib drawing code.
10. dropdown `destination` (multiple): paper, slides, report, dashboard, other.
11. checkboxes (both required): "I searched existing requests"; "Any data here is made up and contains nothing real or confidential".

`config.yml`: `contact_links` to Discussions for usage questions; `blank_issues_enabled` is an owner decision (§7).

### 6.5 The skill's procedure

1. Compose first (D10). If nothing is close, draw with `forgegraph draw` and show the result. Say it's watermarked and why.
2. Offer a request, and ask the user before doing anything on GitHub.
3. **Search, open and closed:** `gh search issues --repo sskaye/forgegraph --match title,body "<name> OR <synonyms>" --json number,title,state,stateReason,url`.
   - A match closed as not planned: tell the user the reason, and don't file again.
   - A match that is open: comment on it (step 5a).
4. Run `forgegraph request --draft …`. Show the user issue.md (or comment.md), the mock-up, sample.csv and the flagged literals, and get a clear yes.
5. Post:
   - a. Matching issue: `gh issue comment N --body-file comment.md --attach mockup.png`, plus the 👍 reaction. The comment must add a use case, not just "+1", following plotly's rule.
   - b. No match: `gh issue create --repo sskaye/forgegraph --title "[Graph type]: <name>" --body-file issue.md --attach mockup.png`. Where the user can apply labels, use the GraphQL `createIssue` call with `issueTemplate: "Graph type request"` [23].
   - Images: `--attach` needs gh ≥ 2.99.0. With an older gh, suggest upgrading, or use the browser path.
6. **Without a working `gh`:** open `…/issues/new?template=graph-type-request.yml&title=…&name=…`, prefilling short fields by id. The user pastes the rest and drags in mockup.png and sample.csv.
7. Report the issue or comment URL.

### 6.6 Maintainer triage recipe

This is a skill or prompt for the maintainer's agent. The maintainer approves every post and every close.

1. List requests: `gh issue list -R sskaye/forgegraph -S '"[Graph type]" in:title is:open' --json number,title,body,labels,reactionGroups,comments`. Order them by 👍 (`gh search issues --sort reactions-+1`). The title prefix and marker find requests filed through `gh` that have no labels.
2. Parse each body by its `### label` sections. Check it against `forgegraph catalog list --json`, the presets and the layers. Each issue gets one outcome:
   - **Composable** with what exists: comment with the recipe; close as completed.
   - **Duplicate:** `gh issue close N --duplicate-of M`, with a note inviting the requester to the original.
   - **Out of scope:** close as not planned, with the reason.
   - **Unclear:** label "needs info", comment with questions, and close after a stated wait (matplotlib uses at least a week).
3. **Accept:**
   - `gh issue develop N --name proposal/<name> --checkout`.
   - Complete graph_type.yaml (`status: proposed`), render the mock-up from the issue's sample data, and add a catalog tab.
   - Push, then comment with the images (`--attach`) and a link to the review page. Label "proposed".
4. The maintainer approves (`status: approved`, label "approved"). The implementing PR says "Closes #N" and sets `status: implemented`.

Labels: graph type request, needs triage, needs info, proposed, approved. Duplicate and not planned use GitHub's close reasons rather than labels.

## 7. Open questions for the owner

1. **Watermark floors.** Pick the values for the opacity and span floors and the contrast ratio. Should a theme be able to change the text at all (the catalog card shows "DRAFT")? Or should it be fixed to NON-STANDARD, or required to contain it?
2. **Several panels:** one watermark across all the panel boxes, or one per panel?
3. **Content hash for files edited after saving:** adopt it? If so, should `forgegraph load` *error* on a mismatch or report it?
4. **`provenance: off` on a non-standard graph:** keep a minimal `nonstandard: true` record, or accept "no record" as the signal?
5. **How drawing code is captured:** a script file through `forgegraph draw`, a Python function, or both?
6. **Bots:** D10 says no bot. Is a GitHub Action allowed for labelling and parsing (needs triage on issues filed through `gh`)? Or do requests rely on the title prefix and the triage agent alone?
7. **`blank_issues_enabled`:** false (as in Vega-Lite) or true (as in matplotlib)? Should Discussions be on, for questions?
8. **Column names in sample data:** generic only, or real names when the user approves them?
9. **gh version:** require gh ≥ 2.99.0 for agent-filed requests, or treat the browser path as a normal option?
10. **Where the triage recipe lives:** a maintainer skill in the repo (.claude/skills), or a docs page?
11. **Agent search scope:** should the agent's search also count closed-as-completed issues, where the type now exists and the agent should simply use it?
12. **Pack and fork users:** requests from organisations always go to the public repo (D10). Should the skill warn that an issue is public before the user approves it?

## Sources

1. GitHub CLI manual, gh issue create: https://cli.github.com/manual/gh_issue_create (and gh_issue_comment)
2. GitHub CLI v2.99.0 release notes: https://github.com/cli/cli/releases/tag/v2.99.0
3. seaborn function overview: https://seaborn.pydata.org/tutorial/function_overview.html
4. seaborn.axes_style: https://seaborn.pydata.org/generated/seaborn.axes_style.html
5. plotnine ggplot reference: https://plotnine.org/reference/ggplot.html
6. Plotly, Creating and updating figures: https://plotly.com/python/creating-and-updating-figures/
7. Vega-Lite, Compiling to Vega: https://vega.github.io/vega-lite/usage/compile.html
8. Vega-Lite top-level spec (usermeta): https://vega.github.io/vega-lite/docs/spec.html
9. matplotlib, Customizing with style sheets and rcParams: https://matplotlib.org/stable/users/explain/customizing.html
10. matplotlib gallery, Custom Figure subclasses: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/custom_figure_class.html
11. C2PA Specification 2.2 (§2.3.12, §9.1, §15): https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
12. C2PA Soft Binding API: https://spec.c2pa.org/specifications/specifications/2.3/softbinding/Decoupled.html
13. CASRAI, C2PA content credentials explained: https://casrai.org/guides/c2pa-content-credentials-explained
14. PNG Specification, Third Edition (§11.3.3, §14.2): https://www.w3.org/TR/png-3/
15. Apache Tika XMPMM (xmpMM DocumentID, InstanceID, History): https://tika.apache.org/2.9.0/api/org/apache/tika/metadata/XMPMM.html
16. HexaPDF metadata (PDF 2.0 Info dictionary deprecation): https://hexapdf.gettalong.org/documentation/metadata/index.html, and the PDF Association errata for ISO 32000-2 clause 14: https://pdf-issues.pdfa.org/32000-2-2020/clause14.html
17. GitHub Docs, Syntax for issue forms: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
18. GitHub Docs, Syntax for GitHub's form schema: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema
19. GitHub Docs, Creating an issue (URL query): https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue
20. GitHub Docs, Configuring issue templates: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
21. github-issue-parser: https://github.com/stefanbuck/github-issue-parser ; form body example: https://github.com/pandas-dev/pandas/issues/71259
22. cli/cli#5865, Support for issue forms: https://github.com/cli/cli/issues/5865
23. cli/cli#13589, labels dropped for Read users; GraphQL issueTemplate: https://github.com/cli/cli/issues/13589 ; GraphQL issues reference: https://docs.github.com/en/graphql/reference/issues
24. GitHub REST, Reactions: https://docs.github.com/en/rest/reactions/reactions
25. GitHub Docs, Searching issues and pull requests: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
26. matplotlib issue templates: https://github.com/matplotlib/matplotlib/tree/main/.github/ISSUE_TEMPLATE
27. pandas issue templates: https://github.com/pandas-dev/pandas/tree/main/.github/ISSUE_TEMPLATE
28. plotly.py issue templates: https://github.com/plotly/plotly.py/tree/main/.github/ISSUE_TEMPLATE
29. Vega-Lite issue templates: https://github.com/vega/vega-lite/tree/main/.github/ISSUE_TEMPLATE
30. ggplot2 issue templates: https://github.com/tidyverse/ggplot2/tree/main/.github/ISSUE_TEMPLATE
31. Stack Overflow, How to create a Minimal, Reproducible Example: https://stackoverflow.com/help/minimal-reproducible-example
32. reprex, Do's and don'ts: https://reprex.tidyverse.org/articles/reprex-dos-and-donts.html
33. SDMetrics, NewRowSynthesis: https://docs.sdv.dev/sdmetrics/metrics/metrics-glossary/newrowsynthesis
34. Garfinkel, Abowd and Martindale, Understanding Database Reconstruction Attacks on Public Data (ACM Queue): https://queue.acm.org/detail.cfm?id=3295691
35. NumPy random Generator: https://numpy.org/doc/stable/reference/random/generator.html
36. GitHub Docs, Managing labels: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels
37. GitHub Docs, Marking issues as duplicates: https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate
38. GitHub Docs, Creating a branch for an issue: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-a-branch-for-an-issue
39. matplotlib, Bug triaging and issue curation: https://matplotlib.org/devdocs/devel/triage.html
40. WCAG 2.2, 1.4.11 Non-text Contrast: https://www.w3.org/TR/WCAG22/#non-text-contrast
