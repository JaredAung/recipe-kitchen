import pytest

from recipe_kitchen.utils import parse_json, require_api_key


def test_parse_json_strips_markdown_fences() -> None:
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_require_api_key_uses_named_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xyz")
    assert require_api_key(name="ELEVENLABS_API_KEY") == "xyz"


def test_require_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        require_api_key()
