"""
PLAT-3970: ``mode`` on narrate_paragraph / batch_narrate / cost_estimate.

The SDK sends ``mode`` only when given, rejects unknown values (and the strict
``"sentence"`` on batch / estimate) before any request, and returns the
server's ``status: "skipped"`` / ``billing`` fields unchanged. Transport is
mocked at ``client``.
"""

import pytest

from audiopod.services.audiobook import AudiobookService


class _RecordingClient:
    def __init__(self, reply=None):
        self.calls = []
        self.reply = reply or {"job_id": 1}

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        return self.reply


def _svc(client):
    return AudiobookService(client, async_mode=False)


@pytest.mark.parametrize("mode", ["auto", "sentence", "passage"])
def test_narrate_paragraph_sends_mode(mode):
    client = _RecordingClient()
    _svc(client).narrate_paragraph("p", "para", mode=mode, voice_id=3)
    method, endpoint, kwargs = client.calls[0]
    assert (method, endpoint) == ("POST", "/api/v1/audiobook/projects/p/paragraphs/para/narrate")
    assert kwargs["json_data"] == {"mode": mode, "voice_id": 3}


def test_narrate_paragraph_omits_mode_by_default():
    client = _RecordingClient()
    _svc(client).narrate_paragraph("p", "para")
    assert "mode" not in client.calls[0][2]["json_data"]


def test_narrate_paragraph_returns_skipped_unchanged():
    reply = {
        "task_id": None,
        "job_id": None,
        "paragraph_id": "para",
        "status": "skipped",
        "billing": {"mode": "none", "billed_chars": 0, "reason": "no_audible_change", "skipped": True},
    }
    out = _svc(_RecordingClient(reply)).narrate_paragraph("p", "para", mode="auto")
    assert out["status"] == "skipped"
    assert out["billing"]["reason"] == "no_audible_change"


@pytest.mark.parametrize("mode", ["auto", "passage"])
def test_batch_narrate_sends_mode(mode):
    client = _RecordingClient()
    _svc(client).batch_narrate("p", mode=mode)
    assert client.calls[0][2]["json_data"]["mode"] == mode


def test_batch_narrate_omits_mode_by_default():
    client = _RecordingClient()
    _svc(client).batch_narrate("p")
    assert "mode" not in client.calls[0][2]["json_data"]


@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.narrate_paragraph("p", "para", mode="whole"),
        lambda s: s.batch_narrate("p", mode="sentence"),
        lambda s: s.cost_estimate("p", mode="sentence"),
    ],
)
def test_invalid_mode_raises_before_any_request(call):
    client = _RecordingClient()
    with pytest.raises(ValueError, match="mode must be one of"):
        call(_svc(client))
    assert client.calls == []


def test_cost_estimate_sends_query_params():
    client = _RecordingClient()
    _svc(client).cost_estimate("p", paragraph_id="para", mode="passage")
    method, endpoint, kwargs = client.calls[0]
    assert (method, endpoint) == ("GET", "/api/v1/audiobook/projects/p/cost-estimate")
    assert kwargs["params"] == {"paragraph_id": "para", "mode": "passage"}


def test_cost_estimate_without_options_sends_no_params():
    client = _RecordingClient()
    _svc(client).cost_estimate("p")
    assert client.calls[0][2]["params"] is None


def test_get_cost_reads_project_cost():
    reply = {"project_id": "p", "breakdown": {"sentence_edits": {"count": 2, "free_count": 1}}}
    client = _RecordingClient(reply)
    out = _svc(client).get_cost("p")
    assert client.calls[0][:2] == ("GET", "/api/v1/audiobook/projects/p/cost")
    assert out["breakdown"]["sentence_edits"]["count"] == 2
