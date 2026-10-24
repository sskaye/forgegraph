# Request to Forgemark: what ForgeGraph needs

**From:** the ForgeGraph project · **For:** the Forgemark maintainer

ForgeGraph's review catalog is one generated HTML page, rebuilt often, with comments carried across each rebuild by Forgemark's command-line tool (`forgemark-cli-1.12.0.mjs`, `reattach --all`). This page lists what ForgeGraph has found that Forgemark should handle.

## 1. reattach reports "surroundings differ" when they match

**Repro:** `docs/forgemark-repro-reattach.md` (a spec mirror, saved as it was). Run `forgemark reattach docs/forgemark-repro-reattach.md --all --dry-run`.

**What happens:** comment 5 ("Axis the bars extend along.", on line 10) stays orphaned: "is in the page once, at line 10, but it doesn't have the words recorded around it: before it "…y # \[x, y\];", there "…y # \[x, y\];"". The two quoted texts are identical. Reattaching it by id with `--anchor` works.

**Likely cause:** something in the surroundings that the message doesn't show differs in the comparison but not in the display. The candidates in this file: comment 1's markers (`<!-- fmc:1 -->`) inside the italic text just after the anchor, added after comment 5's surroundings were recorded; the escaped `\[` and the hard-break backslashes; or the non-breaking spaces. A simple case with a neighbouring comment's markers in the surroundings does reattach, so it isn't markers alone.

**A second case that points at the message:** in docs/specs/theme/default.md, after a line was added just below "Cap width, × base size.", reattach said that comment's surroundings differ and again quoted two identical "before" texts. There the text after the anchor really had changed. So the message quotes the before-text even when it's the after-text that differs, which makes the first case impossible to diagnose from the message.

**Fix:** compare surroundings in the same normalized form the message displays, and when they differ, quote the differing part rather than the start.

## 2. An escaped `<` can't be anchored as a reader sees it

**Repro:** a line in a spec mirror holds an escaped angle bracket, which a reader sees as `<name>`:

```
file: auto *# The status file. auto: \<name>.status.json beside this file.*
```

- `forgemark comment repro.md --anchor "auto: <name>.status.json" --body x` fails: "was not found".
- `--anchor "auto: \<name>.status.json"` succeeds, but records the anchor as "auto: \.status.json": `<name>` is dropped as if it were an HTML tag, and the backslash is kept.

The same happens with escaped brackets: on a line holding `areas: \[\[voltage, polarization\],`, `--anchor "[[voltage, polarization],"` is "not found", while `--anchor "voltage, polarization"` attaches.

**Likely cause:** the anchor matcher strips HTML tags from the page text before removing Markdown escapes, so `\<name>` loses `<name>` and keeps `\`. The quoted anchor is normalized differently, so the two never match.

**Fix:** remove Markdown backslash escapes first, so `\<name>` becomes the literal text `<name>`, then strip only real tags. Record the anchor text in that same reader's form.

**Tests:** an anchor containing `\<`, `\_`, `\*` and `\[` matches when quoted without the backslashes, and its recorded anchor text is what the reader sees.

**Workaround in use:** in docs/specs/schedule/default.md, comment 10 is anchored on "The status file. auto:", which stops before the bracket.

## 3. A page's own tabs don't switch

**Repro:** open `review/phase-07/deliverable/dashboard/lab_throughput.html` in Forgemark. The page shows a tab bar (Overview, By instrument). Click "By instrument".

**What happens:** nothing. The Overview tab stays showing. In a browser, the same file switches tabs, and opening `lab_throughput.html#by-instrument` opens that tab directly.

**How the page's tabs work:** each tab in the bar is an ordinary link to an id on the page (`<a role="tab" href="#by-instrument">`). A short script in the page shows the section whose id is in the URL's fragment, and listens for `hashchange`. Where no script runs, the page shows every tab's section, one after another, under its name. ForgeGraph writes these pages for dashboards, which people open in a browser, so the tabs need the page's script and its links.

**Likely cause:** Forgemark doesn't run the page's own `<script>`, or it intercepts in-page `#` links, so the fragment never changes. The review catalog's tabs work in Forgemark because they use no script: they're radio buttons shown and hidden by CSS. The two cases tell these causes apart:
- If the script is removed, the page should show both tabs stacked. If Forgemark shows only Overview instead, the script ran, and only the link navigation is blocked.
- If the script runs but the click does nothing, the link navigation is blocked.

**Fix:** let a page's own fragment links change the fragment (and fire `hashchange`) without leaving the page, and run the page's inline scripts. A page in Forgemark is the user's own report, so its scripts are as trusted as the page itself. If scripts must stay off, show the page as it would look without them, with every tab visible, rather than half-working.

**Tests:**
- A page whose script shows the section named by the fragment switches on a click, and opens on the right section with a fragment in its address.
- A comment anchored inside a hidden tab's section is still listed, and opening it shows that tab.
