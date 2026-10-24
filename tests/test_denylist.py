import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_denylist.py"
spec = importlib.util.spec_from_file_location("check_denylist", SCRIPT)
assert spec and spec.loader
check_denylist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_denylist)


@pytest.fixture
def terms(monkeypatch):
    monkeypatch.setenv("FORGEGRAPH_DENYLIST", "zebraquux, Plinth")
    monkeypatch.delenv("FORGEGRAPH_DENYLIST_REQUIRED", raising=False)


def test_rejects_a_file_containing_a_term(tmp_path, terms, capsys):
    bad = tmp_path / "notes.md"
    bad.write_text("fine\nsee mail.ZebraQuux.example for details\n")
    assert check_denylist.main([str(bad)]) == 1
    out = capsys.readouterr().out
    assert "notes.md:2" in out and "term #1" in out
    assert "zebraquux" not in out.lower()  # the term itself is never printed


def test_finds_terms_inside_longer_words(tmp_path, terms):
    bad = tmp_path / "data.csv"
    bad.write_text("name\nmegaplinthic\n")
    assert check_denylist.main([str(bad)]) == 1


def test_accepts_clean_and_binary_files(tmp_path, terms):
    clean = tmp_path / "clean.txt"
    clean.write_text("nothing to see here\n")
    binary = tmp_path / "font.ttf"
    binary.write_bytes(b"\0\1zebraquux")
    assert check_denylist.main([str(clean), str(binary)]) == 0


def test_missing_terms_fail_only_when_required(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGEGRAPH_DENYLIST", "")
    monkeypatch.setattr(check_denylist, "DEFAULT_FILE", tmp_path / "absent.txt")
    monkeypatch.delenv("FORGEGRAPH_DENYLIST_REQUIRED", raising=False)
    assert check_denylist.main([]) == 0
    monkeypatch.setenv("FORGEGRAPH_DENYLIST_REQUIRED", "1")
    assert check_denylist.main([]) == 1


def test_ignores_terms_inside_embedded_base64_images(tmp_path, terms):
    page = tmp_path / "review.html"
    page.write_text('<img src="data:image/png;base64,AAAAzebraquuxBBBB==">\n<p>clean</p>\n')
    assert check_denylist.main([str(page)]) == 0
    page.write_text('<img src="data:image/png;base64,AAAA==">\n<p>zebraquux</p>\n')
    assert check_denylist.main([str(page)]) == 1
