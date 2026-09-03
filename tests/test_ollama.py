import io
import json
import urllib.request

from daisy_pet.ollama import build_prompt, generate_line


def test_non_local_url_never_calls_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("network call attempted")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    assert generate_line("hi", "model", "http://example.com:11434") is None


def test_success_parse_and_collapse(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"response": " hello\nthere  "}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: Response())
    assert generate_line("hi", "model", "http://127.0.0.1:11434") == "hello there"


def test_timeout_or_garbage_returns_none(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: io.BytesIO(b"not json"),
    )
    assert generate_line("hi", "model", "http://localhost:11434") is None


def test_prompt_contains_constraints():
    prompt = build_prompt("gentle", 4)
    assert "ONE short" in prompt
    assert "gentle" in prompt
    assert "12 words" in prompt
    assert "no emoji" in prompt
