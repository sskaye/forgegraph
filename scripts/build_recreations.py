"""Build the phase 2 recreation set: the review page and the image-regression baselines.

uv run python scripts/build_recreations.py              # review/phase-02/recreations.html
uv run python scripts/build_recreations.py --baselines  # tests/baselines/*.png

--baselines also draws the side-by-side examples as layouts (LAYOUT_RECREATIONS), into
tests/baselines and review/phase-07/deliverable/recreations.
"""

from __future__ import annotations

import base64
import html
import io
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

import tempfile  # noqa: E402

from recreations import LAYOUT_RECREATIONS, RECREATIONS  # noqa: E402

from forgegraph.catalog.build import write  # noqa: E402
from forgegraph.drawing.style import isolated  # noqa: E402

BASELINE_DPI = 72
CSS_DPI = 96  # a CSS inch, so images show at the figure's real size


def _png(graph, dpi: int) -> bytes:
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(buffer, format="png", dpi=dpi)
    return buffer.getvalue()


def baselines() -> None:
    folder = ROOT / "tests" / "baselines"
    folder.mkdir(exist_ok=True)
    for r in RECREATIONS:
        (folder / f"{r.name}.png").write_bytes(_png(r.render(), BASELINE_DPI))
        print(f"wrote tests/baselines/{r.name}.png")
    review = ROOT / "review" / "phase-07" / "deliverable" / "recreations"
    review.mkdir(parents=True, exist_ok=True)
    for lr in LAYOUT_RECREATIONS:
        with tempfile.TemporaryDirectory() as folder:
            tab = lr.render(Path(folder)).tabs[0]
            with tab.saving():
                tab.figure.savefig(baseline(lr.name), format="png", dpi=BASELINE_DPI)
                tab.figure.savefig(review / f"{lr.name}.png", format="png", dpi=2 * CSS_DPI)
        print(f"wrote tests/baselines/{lr.name}.png and {review.relative_to(ROOT)}/{lr.name}.png")


def baseline(name: str) -> Path:
    """A baseline image's path."""
    return ROOT / "tests" / "baselines" / f"{name}.png"


STYLE = """
:root { --fg:#1f2328; --muted:#57606a; --line:#d0d7de; --bg:#fff; --accent:#0969da; }
body { font-family:-apple-system,"Segoe UI",system-ui,sans-serif; color:var(--fg);
       background:var(--bg); margin:0; padding:1.5rem 24px 3rem; line-height:1.5; }
.prose { max-width:900px; }
h2 { margin-top:2.2rem; border-bottom:1px solid var(--line); }
.sub { color:var(--muted); margin-top:0; }
.grid { display:grid; gap:1.4rem;
        grid-template-columns:repeat(auto-fill, minmax(min(100%, 560px), 1fr)); }
.card { border:1px solid var(--line); border-radius:6px; padding:.6rem 1rem 1rem; }
.card h3 { margin:.3rem 0 .4rem; font-size:1.05rem; }
figure { margin:0; } figure img { max-width:100%; height:auto; }
figcaption { display:none; }
.settings { font-size:.9rem; color:var(--muted); margin:.6rem 0 0; padding-left:1.2rem; }
"""


def page() -> str:
    cards = []
    for r in RECREATIONS:
        g = r.render()
        image = base64.b64encode(
            _png(g, 2 * CSS_DPI)
        ).decode()  # double density: sharp on any screen
        width = round(g.figure.get_size_inches()[0] * CSS_DPI)  # shown at its true size
        settings = "".join(
            f"<li>{html.escape(path)}: {html.escape(str(value))}</li>"
            for path, value in {
                **r.settings,
                **({"text.title": r.title} if r.title else {}),
                **{f"format {k}": v for k, v in r.format.items()},
            }.items()
        )
        notes = "".join(f"<li>{html.escape(w)}</li>" for w in g.warnings)
        cards.append(
            f'<section class="card" id="case-{r.name}">\n'
            f"<h3>{html.escape(r.name.replace('_', ' '))}</h3>\n"
            f"<p>{html.escape(r.caption)} Series named by: {g.labelling}.</p>\n"
            f'<figure id="case-{r.name}-figure"><img alt="{html.escape(r.name)}" width="{width}" '
            f'src="data:image/png;base64,{image}"><figcaption>{html.escape(r.name)}</figcaption></figure>\n'
            f'<ul class="settings" id="case-{r.name}-settings">{settings}{notes}</ul>\n</section>'
        )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Phase 2 recreations</title>\n<style>{STYLE}</style></head><body>\n"
        '<h1 id="title">Phase 2 recreations</h1>\n'
        '<p class="sub">The kinds of graph in the examples, drawn by ForgeGraph from rescaled '
        "synthetic data with the default theme and format. For review with the phase 3 "
        "catalog.</p>\n"
        '<div class="prose"><p id="intro">Each card lists the GraphSpec settings that differ '
        "from the defaults. The theme is the starting look, to be tuned together in phase "
        "3.</p></div>\n"
        f'<div class="grid" id="cases">\n{chr(10).join(cards)}\n</div>\n</body></html>\n'
    )


if __name__ == "__main__":
    if "--baselines" in sys.argv:
        baselines()
    else:
        out = ROOT / "review" / "phase-02" / "recreations.html"
        lint = write(out, page())  # keeps the page's comments
        print(f"wrote {out.relative_to(ROOT)}" + (f"\n{lint}" if lint else ""))
