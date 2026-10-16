"""PLAT-3961: a structured ``detail`` object surfaces its ``message``."""

import json

import pytest
import requests

from audiopod import Client
from audiopod.exceptions import APIError


def _response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode()
    r.headers["Content-Type"] = "application/json"
    return r


def test_object_detail_shows_message():
    client = Client(api_key="ap_test")
    with pytest.raises(APIError) as exc:
        client._handle_response(_response(400, {"detail": {"message": "Voice not ready", "code": "x"}}))
    assert "Voice not ready" in str(exc.value)
    assert "{" not in str(exc.value)


def test_string_detail_unchanged():
    client = Client(api_key="ap_test")
    with pytest.raises(APIError) as exc:
        client._handle_response(_response(404, {"detail": "Not found"}))
    assert "Not found" in str(exc.value)
