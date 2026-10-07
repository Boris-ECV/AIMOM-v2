"""SDLCAIP2-64: static checks for the allow-list management UI in index.html."""
import re
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")


def _section() -> str:
    start = HTML.index("function fmtIsoLocal")
    end_fn = HTML.index("function wireAllowedUsers")
    end = HTML.index("\n}\n", end_fn) + 3
    return HTML[start:end]


def test_key_ids_present():
    for id_ in (
        "allowed-users-card",
        "allowed-users-form",
        "allowed-users-input",
        "allowed-users-add-btn",
        "allowed-users-msg",
        "allowed-users-status",
        "allowed-users-retry-btn",
        "allowed-users-table",
        "allowed-users-tbody",
    ):
        assert f'id="{id_}"' in HTML


def test_input_is_text_not_email_and_form_novalidate():
    m = re.search(r'<input id="allowed-users-input"[^>]*>', HTML)
    assert m
    assert 'type="text"' in m.group(0)
    assert 'type="email"' not in m.group(0)
    assert re.search(r'<form id="allowed-users-form"[^>]*novalidate', HTML)


def test_delete_uses_encode_uri_component():
    idx = HTML.index("'/api/admin/allowed-users/'")
    assert "encodeURIComponent" in HTML[idx : idx + 120]
    assert "method: 'DELETE'" in HTML[idx : idx + 200]


def test_section_has_no_unsafe_rendering():
    section = _section()
    assert "onclick=" not in section
    assert "esc(" not in section
    assert "innerHTML" not in section
    assert "textContent" in section
    assert "replaceChildren" in section


def test_title_is_section_title_not_h4():
    card = HTML[HTML.index('id="allowed-users-card"') :]
    card = card[: card.index("</table>")]
    assert "<h4" not in card
    assert '<div class="section-title">使用者白名單</div>' in card
