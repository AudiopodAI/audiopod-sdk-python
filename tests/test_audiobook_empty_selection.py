"""
PLAT-3944: an explicit empty selection list must never mean "the whole book".

The API answers ``[]`` in ``chapter_ids`` / ``paragraph_ids`` /
``include_chapters`` with 400 ``empty_selection`` (PLAT-3943). The SDK fails
fast with ``ValueError`` before any request, omits the field for ``None``, and
sends any non-empty list verbatim. Transport is mocked at ``client``.
"""

import pytest

from audiopod.services.audiobook import AudiobookService


class _RecordingClient:
    def __init__(self):
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        return {"job_id": "1"}


def _call(service, method, param, value):
    if method == "auto_direct":
        return service.auto_direct("p", **{param: value})
    if method == "batch_narrate":
        return service.batch_narrate("p", **{param: value})
    if method == "start_narration":
        return service.start_narration("p", 7, **{param: value})
    if method == "start_export":
        return service.start_export("p", **{param: value})
    raise AssertionError(method)


CASES = [
    ("auto_direct", "chapter_ids"),
    ("batch_narrate", "chapter_ids"),
    ("batch_narrate", "paragraph_ids"),
    ("start_narration", "chapter_ids"),
    ("start_export", "include_chapters"),
]


@pytest.mark.parametrize("method,param", CASES)
def test_empty_list_raises_before_any_request(method, param):
    client = _RecordingClient()
    with pytest.raises(ValueError, match=f"{param} is empty; pass None to use the whole book"):
        _call(AudiobookService(client, async_mode=False), method, param, [])
    assert client.calls == []


@pytest.mark.parametrize("method,param", CASES)
def test_none_omits_the_field(method, param):
    client = _RecordingClient()
    _call(AudiobookService(client, async_mode=False), method, param, None)
    assert param not in client.calls[0][2]["json_data"]


@pytest.mark.parametrize("method,param", CASES)
def test_non_empty_list_is_sent(method, param):
    client = _RecordingClient()
    _call(AudiobookService(client, async_mode=False), method, param, ["c1", "c2"])
    assert client.calls[0][2]["json_data"][param] == ["c1", "c2"]


def test_async_mode_also_rejects_empty_list():
    client = _RecordingClient()
    with pytest.raises(ValueError):
        AudiobookService(client, async_mode=True).auto_direct("p", chapter_ids=[])
    assert client.calls == []
