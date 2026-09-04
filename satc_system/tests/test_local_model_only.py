"""The local model is local, and that is enforced rather than asserted.

`settings.ollama_enabled` has always said, in its docstring, that "Ollama runs
entirely on localhost -- no document leaves the machine." Four lines below it,
`ollama_host()` returned `$SATC_OLLAMA_HOST` unchecked. One environment
variable therefore sent client tax documents to someone else's server, and did
it silently: a working remote Ollama answers exactly like a local one.

The Forge's standing rule binds the Ollama SERVER to 127.0.0.1 so nothing can
reach the model. This is the other half of the same door -- the client.
"""

from __future__ import annotations

import pytest

from satc import settings


def test_the_default_is_local(monkeypatch):
    monkeypatch.delenv("SATC_OLLAMA_HOST", raising=False)
    assert settings.ollama_host() == "http://localhost:11434"


@pytest.mark.parametrize("url", [
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "http://127.0.0.53:11434",       # anything in 127/8 is still this machine
    "http://[::1]:11434",
    "https://LOCALHOST:11434",       # scheme and case are not the question
])
def test_a_loopback_host_is_allowed(monkeypatch, url):
    monkeypatch.setenv("SATC_OLLAMA_HOST", url)
    assert settings.ollama_host() == url


@pytest.mark.parametrize("url", [
    "http://192.168.1.50:11434",     # the LAN -- the realistic mistake
    "http://10.0.0.4:11434",
    "http://100.125.166.122:11434",  # the tailnet: still not this machine
    "https://ollama.example.com",
    "http://[2001:db8::1]:11434",
])
def test_anything_else_is_refused(monkeypatch, url):
    monkeypatch.setenv("SATC_OLLAMA_HOST", url)
    with pytest.raises(settings.RemoteModelRefused) as e:
        settings.ollama_host()
    assert url in str(e.value), "the refusal must name what was rejected"


def test_a_hostname_we_cannot_pin_to_loopback_is_refused(monkeypatch):
    """NOT resolved through DNS on purpose.

    A name that resolves to 127.0.0.1 today can resolve elsewhere tomorrow, and
    a check satisfied by DNS is worth nothing. Only a literal loopback address
    or `localhost` passes.
    """
    monkeypatch.setenv("SATC_OLLAMA_HOST", "http://my-ollama-box:11434")
    with pytest.raises(settings.RemoteModelRefused):
        settings.ollama_host()


def test_it_refuses_rather_than_quietly_using_the_safe_default(monkeypatch):
    """A silent fallback would honour the safe behaviour and hide that somebody
    asked for the unsafe one. The person who set this needs to find out."""
    monkeypatch.setenv("SATC_OLLAMA_HOST", "http://192.168.1.50:11434")
    with pytest.raises(settings.RemoteModelRefused):
        settings.ollama_host()
