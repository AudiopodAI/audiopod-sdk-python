import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiohttp
from aiohttp import web
import pytest

from audiopod import Client, AsyncClient
from audiopod.exceptions import APIError
from audiopod.services.dubbing import DubbingService
from audiopod.services.voice import VoiceService
from audiopod import cli

IDENTIFIER = "AAAAAAAA-1111-2222-3333-BBBBBBBBBBBB"
CANONICAL = IDENTIFIER.lower()
KEY = "CCCCCCCC-4444-5555-6666-DDDDDDDDDDDD"


@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_exact_confirmed_dubbing_body_and_uuid_no_automatic_second_accept(async_mode):
    request = AsyncMock(return_value={}) if async_mode else Mock(return_value={})
    api = DubbingService(SimpleNamespace(request=request),async_mode=async_mode)
    quote = api.quote(IDENTIFIER,retranslate=True)
    if async_mode: await quote
    body = {"confirm":True,"confirmations":[{"edition_id":IDENTIFIER,"expected_revision":3,
        "quote_identity":"q"*64,"idempotency_key":KEY,"retranslate":True}]}
    accepted = api.analyze(IDENTIFIER,body)
    if async_mode: await accepted
    assert request.call_args_list[0].args == ("GET",f"/api/v1/dubbing/editions/{CANONICAL}/quote")
    assert request.call_args_list[0].kwargs["params"]["retranslate"] == "true"
    confirmation = request.call_args_list[1].kwargs["json_data"]["confirmations"][0]
    assert confirmation["idempotency_key"] == KEY.lower() and confirmation["quote_identity"] == "q"*64
    with pytest.raises(ValueError): api.analyze(IDENTIFIER,{"confirm":False,"confirmations":[]})
    assert request.call_count == 2
    translated = api.retranslate(IDENTIFIER,{"expected_revision":3,"quote_identity":"q"*64,"confirm":True})
    if async_mode: await translated
    assert request.call_args.args == ("POST",f"/api/v1/dubbing/jobs/{CANONICAL}/retranslate")
    with pytest.raises(ValueError): api.retranslate(IDENTIFIER,{"confirm":False})


@pytest.mark.parametrize("status",["review_required","export_partial","completed"])
@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_wait_stops_for_user_decisions_without_generating(status,async_mode):
    request = AsyncMock(return_value={"id":CANONICAL,"status":status}) if async_mode else Mock(return_value={"id":CANONICAL,"status":status})
    api = DubbingService(SimpleNamespace(request=request),async_mode=async_mode)
    result = api.wait_for_job(IDENTIFIER)
    if async_mode: result = await result
    assert result["status"] == status and request.call_count == 1
    assert request.call_args.args[0] == "GET"


@pytest.mark.asyncio
async def test_async_terminal_wait_retains_job_and_error_code():
    api = DubbingService(SimpleNamespace(request=AsyncMock(return_value={"status":"expired","error_code":"review_expired"})),async_mode=True)
    with pytest.raises(APIError) as error: await api.wait_for_job(IDENTIFIER)
    assert error.value.code == "review_expired" and error.value.detail["job"]["status"] == "expired"


@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_wait_timeout_retains_accepted_job_without_new_work(async_mode):
    request = AsyncMock(return_value={"status":"settle_pending"}) if async_mode else Mock(return_value={"status":"settle_pending"})
    api = DubbingService(SimpleNamespace(request=request),async_mode=async_mode)
    with pytest.raises(APIError) as error:
        if async_mode: await api.wait_for_job(IDENTIFIER,timeout=0)
        else: api.wait_for_job(IDENTIFIER,timeout=0)
    assert error.value.code == "wait_timeout" and error.value.action == "poll_job"
    assert error.value.detail["job"]["status"] == "settle_pending" and request.call_count == 1


@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_strict_clone_original_bytes_close_file_and_keep_key_for_status(tmp_path,async_mode):
    raw = b"original bytes"
    path = tmp_path/"reference.wav"; path.write_bytes(raw)
    captured = []
    def capture(method,endpoint,**kwargs):
        stream = kwargs.get("files",{}).get("file",(None,None))[1]
        captured.append((method,endpoint,kwargs,stream,stream.read() if stream else None))
        return {"state":"registration_uncertain"}
    async def async_capture(*args,**kwargs): return capture(*args,**kwargs)
    api = VoiceService(SimpleNamespace(request=async_capture if async_mode else capture),async_mode=async_mode)
    admitted = api.admit_reference(str(path),consent_id=IDENTIFIER,consent_revision=2,consent_version="policy",
        transcription="मेरी आवाज़",confirm_transcription=True,replace_voice_id=17,reference_revision=4)
    if async_mode: await admitted
    registered = api.register_reference(str(path),admission_token="opaque",idempotency_key=KEY,name="Narrator")
    if async_mode: await registered
    status = api.registration_status(KEY)
    if async_mode: await status
    assert captured[0][4] == captured[1][4] == raw
    assert captured[0][3].closed and captured[1][3].closed
    assert captured[0][2]["data"]["reference_revision"] == 4
    assert captured[1][2]["data"]["idempotency_key"] == KEY.lower()
    assert captured[2][0] == "GET" and captured[2][1].endswith(KEY.lower())


def test_private_reuse_scopes_and_manual_invitation_are_preserved():
    request = Mock(return_value={})
    api = DubbingService(SimpleNamespace(request=request))
    api.set_glossary("hi",{"expected_version":0,"mode":"override","entries":[{"source":"AudioPod","mode":"keep_unchanged"}]},IDENTIFIER)
    api.reset_glossary("hi",4,IDENTIFIER)
    api.invite_reviewer(IDENTIFIER,"recipient@isolated.invalid")
    api.get_review("token/?private")
    assert request.call_args_list[0].kwargs["params"]["project_id"] == CANONICAL
    assert request.call_args_list[0].kwargs["json_data"]["expected_version"] == 0
    assert request.call_args_list[1].args[0] == "DELETE"
    assert request.call_args_list[2].kwargs["json_data"] == {"recipient_email":"recipient@isolated.invalid"}
    assert request.call_args_list[3].args[1].endswith("token%2F%3Fprivate")


@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_real_loopback_transport_preserves_structured_409_without_post_retry(async_mode):
    calls = []
    async def handle(request):
        calls.append(await request.json())
        assert request.headers.get("X-API-Key") is None
        assert request.headers["Authorization"] == "Bearer isolated-jwt"
        return web.json_response({"detail":{"code":"quote_changed","action":"new_quote","revision":4}},status=409,headers={"Retry-After":"7"})
    app = web.Application(); app.router.add_post("/api/v1/dubbing/jobs/{id}/generate",handle)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner,"127.0.0.1",0); await site.start()
    url = "http://127.0.0.1:"+str(site._server.sockets[0].getsockname()[1])
    client = (AsyncClient if async_mode else Client)(access_token="isolated-jwt",base_url=url,max_retries=9)
    try:
        with pytest.raises(APIError) as error:
            if async_mode: await client.dubbing.generate(IDENTIFIER,{"expected_revision":3,"quote_identity":"old","confirm":True})
            else: await asyncio.to_thread(client.dubbing.generate,IDENTIFIER,{"expected_revision":3,"quote_identity":"old","confirm":True})
        assert error.value.code == "quote_changed" and error.value.action == "new_quote"
        assert error.value.retry_after == "7" and error.value.status_code == 409
        assert error.value.detail == {"code":"quote_changed","action":"new_quote","revision":4}
        assert len(calls) == 1
    finally:
        if async_mode: await client.close()
        else: client.session.close()
        await runner.cleanup()


@pytest.mark.parametrize("async_mode",[False,True])
@pytest.mark.asyncio
async def test_presigned_put_uses_fresh_transport_with_original_bytes(tmp_path,async_mode,monkeypatch):
    raw = b"original bytes"*1000
    path = tmp_path/"source.wav"; path.write_bytes(raw)
    async def handle(request):
        assert request.headers.get("Authorization") is None and request.headers.get("X-API-Key") is None
        assert await request.read() == raw
        return web.Response(headers={"ETag":"isolated"})
    app = web.Application(); app.router.add_put("/bytes",handle)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner,"127.0.0.1",0); await site.start()
    url = "http://127.0.0.1:"+str(site._server.sockets[0].getsockname()[1])+"/bytes"
    client = (AsyncClient if async_mode else Client)(api_key="ap_isolated")
    netrc = tmp_path/"netrc"
    netrc.write_text("machine 127.0.0.1 login ambient password must-not-leak\n")
    monkeypatch.setenv("NETRC",str(netrc))
    upload = {"upload_id":CANONICAL,"url":url,"method":"PUT","headers":{"Content-Type":"audio/wav"},"key_expires_in":60}
    try:
        result = await client.uploads.put(upload,str(path)) if async_mode else await asyncio.to_thread(client.uploads.put,upload,str(path))
        assert result == {"upload_session_id":CANONICAL,"etag":"isolated"}
    finally:
        if async_mode: await client.close()
        else: client.session.close()
        await runner.cleanup()


def test_cli_confirmation_is_required_before_client_creation(monkeypatch):
    client = Mock(side_effect=AssertionError("must not create client"))
    monkeypatch.setattr(cli,"_client",client)
    with pytest.raises(SystemExit) as error: cli.main(["dubbing","analyze",IDENTIFIER])
    assert error.value.code == 2 and client.call_count == 0


def test_cli_exact_confirmation_is_explicit_and_structured_error_survives(tmp_path,monkeypatch,capsys):
    path = tmp_path/"accept.json"
    body = {"confirmations":[{"edition_id":IDENTIFIER,"expected_revision":3,"quote_identity":"q"*64,"idempotency_key":KEY}]}
    path.write_text(__import__("json").dumps(body))
    analyze = Mock(side_effect=APIError("quote_changed",409,detail={"code":"quote_changed","action":"new_quote"}))
    monkeypatch.setattr(cli,"_client",lambda args:SimpleNamespace(dubbing=SimpleNamespace(analyze=analyze)))
    with pytest.raises(SystemExit): cli.main(["dubbing","analyze",IDENTIFIER,"--body",str(path),"--confirm","--json"])
    assert analyze.call_args.args[1] == {**body,"confirm":True}
    error = __import__("json").loads(capsys.readouterr().err)["error"]
    assert error["status_code"] == 409 and error["code"] == "quote_changed" and error["action"] == "new_quote"


def test_dubbing_pronunciation_canonicalizes_project_without_changing_account_scope():
    request = Mock(return_value={})
    api = VoiceService(SimpleNamespace(request=request))
    api.resolve_pronunciation("hi",project_kind="dubbing",project_id=IDENTIFIER)
    api.quote_audition(17,text="AudioPod",language="hi",project_kind="dubbing",project_id=IDENTIFIER)
    assert request.call_args_list[0].kwargs["json_data"]["project_id"] == CANONICAL
    assert request.call_args_list[1].kwargs["json_data"]["project_id"] == CANONICAL
