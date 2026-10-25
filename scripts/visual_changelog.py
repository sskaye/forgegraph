"""Before and after images of every graph that changed between two commits.

uv run python scripts/visual_changelog.py main            # main against the working tree
uv run python scripts/visual_changelog.py v0.1.0 v0.2.0   # between two commits
    [--out docs/visual-changelog/<version>.html]

Compares the regression baselines (tests/baselines/*.png) and each catalog page's figures (by
id), and writes one page showing each changed, added or removed image.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import subprocess
from pathlib import Path

import forgegraph

ROOT = Path(__file__).parents[1]
BASELINES = "tests/baselines"
CATALOG = "catalog/forgegraph_base.html"
EARLIER_CATALOG = "catalog/catalog.html"  # forgegraph_base's page before phase 6
FIGURE = re.compile(r'<figure id="([^"]+)"><img [^>]*src="data:image/png;base64,([^"]+)"')


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def _baselines(ref: str | None) -> dict[str, bytes]:
    if ref is None:
        return {f"{p.stem}": p.read_bytes() for p in sorted((ROOT / BASELINES).glob("*.png"))}
    names = _git("ls-tree", "--name-only", f"{ref}:{BASELINES}").decode().split()
    return {
        Path(n).stem: _git("show", f"{ref}:{BASELINES}/{n}") for n in names if n.endswith(".png")
    }


def _pages(ref: str | None) -> set[str]:
    """The catalog pages at a commit, or in the working tree, by path."""
    if ref is None:
        return {f"catalog/{p.name}" for p in (ROOT / "catalog").glob("*.html")}
    names = _git("ls-tree", "--name-only", f"{ref}:catalog").decode().split()
    pages = {f"catalog/{n}" for n in names if n.endswith(".html")}
    return {CATALOG if p == EARLIER_CATALOG else p for p in pages}


def _catalog(ref: str | None, page: str) -> dict[str, bytes]:
    text = None
    for name in (page, EARLIER_CATALOG) if page == CATALOG else (page,):
        try:
            text = (
                (ROOT / name).read_text(encoding="utf-8")
                if ref is None
                else _git("show", f"{ref}:{name}").decode()
            )
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    if text is None:
        return {}
    return {fid: base64.b64decode(data) for fid, data in FIGURE.findall(text)}


def _img(data: bytes | None, label: str) -> str:
    if data is None:
        return f'<figure><p class="none">{label}: none</p></figure>'
    src = base64.b64encode(data).decode()
    return (
        f'<figure><img alt="{label}" src="data:image/png;base64,{src}">'
        f"<figcaption>{label}</figcaption></figure>"
    )


def _section(title: str, sid: str, old: dict[str, bytes], new: dict[str, bytes]) -> str:
    changed = [k for k in sorted(old.keys() | new.keys()) if old.get(k) != new.get(k)]
    if not changed:
        return f'<h2 id="{sid}">{title}</h2>\n<p>No changes.</p>'
    cards = []
    for k in changed:
        what = "added" if k not in old else "removed" if k not in new else "changed"
        cards.append(
            f'<section class="card" id="{sid}-{html.escape(k)}">\n'
            f'<h3>{html.escape(k)} ({what})</h3>\n<div class="pair">\n'
            f"{_img(old.get(k), 'Before')}\n{_img(new.get(k), 'After')}\n</div>\n</section>"
        )
    return f'<h2 id="{sid}">{title}</h2>\n' + "\n".join(cards)


STYLE = """
body { font-family:-apple-system,"Segoe UI",system-ui,sans-serif; margin:0;
       padding:1.5rem 24px 3rem; line-height:1.5; color:#1f2328; background:#fff; }
.card { border:1px solid #d0d7de; border-radius:6px; padding:.6rem 1rem 1rem; margin:1rem 0; }
.pair { display:flex; flex-wrap:wrap; gap:1rem; }
figure { margin:0; } figure img { max-width:100%; height:auto; }
figcaption, .none { color:#57606a; font-size:.9rem; }
"""


def page(before: str, after: str | None) -> str:
    label = f"{before} → {after or 'working tree'}"
    body = "\n".join(
        [
            _section("Regression baselines", "baselines", _baselines(before), _baselines(after)),
            *(
                _section(
                    f"Catalog: {Path(p).stem}",
                    Path(p).stem,
                    _catalog(before, p),
                    _catalog(after, p),
                )
                for p in sorted(_pages(before) | _pages(after))
            ),
        ]
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Visual changelog</title>\n<style>{STYLE}</style></head><body>\n"
        f'<h1 id="title">Visual changelog</h1>\n<p id="range">{html.escape(label)}</p>\n'
        f"{body}\n</body></html>\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Images that changed between two commits.")
    parser.add_argument("before", help="A commit, branch or tag.")
    parser.add_argument("after", nargs="?", help="Another; the working tree if left out.")
    parser.add_argument("--out", type=Path, help="Default: docs/visual-changelog/<version>.html.")
    args = parser.parse_args()
    args.out = args.out or ROOT / "docs" / "visual-changelog" / f"{forgegraph.__version__}.html"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page(args.before, args.after), encoding="utf-8")
    print(f"wrote {args.out}")
