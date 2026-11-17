"""Tests de la passerelle (fake et http) — aucun service réel."""
import httpx

from studio.clients.fake_gateway import FakeGenerationGatewayClient
from studio.clients.http_gateway import HttpGenerationGatewayClient
from studio.clients.interface import GatewayError, ImageRequest, TextRequest


def test_fake_text_structured():
    gw = FakeGenerationGatewayClient()
    r = gw.generate_text(TextRequest(
        prompt="analyse", response_format={"type": "json_schema", "schema": {
            "type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}}))
    assert r.schema_valid is True
    assert isinstance(r.data, dict)
    assert "description" in r.data


def test_fake_image_async_and_track():
    gw = FakeGenerationGatewayClient()
    outcome = gw.generate_image(ImageRequest(prompt="x"), async_exec=True)
    assert outcome.job is not None
    status = gw.get_job(outcome.job.job_id)
    assert status.status == "succeeded"
    assert status.result["images"][0]["url"].startswith("fake://")


def test_fake_video_controlled_failure():
    gw = FakeGenerationGatewayClient()
    outcome = gw.generate_video(None, async_exec=True)  # type: ignore[arg-type]
    status = gw.get_job(outcome.job.job_id)
    assert status.status == "failed"


def test_fake_download_media():
    gw = FakeGenerationGatewayClient()
    data = gw.download_media("fake://media/x.png")
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def _http_client(handler):
    c = HttpGenerationGatewayClient()
    c._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.example.com")
    return c


def test_http_normalizes_job_200():
    def handler(request):
        return httpx.Response(200, json={"job_id": "job_1", "status": "queued"})
    c = _http_client(handler)
    out = c.generate_image(ImageRequest(prompt="x"), async_exec=True)
    assert out.job is not None and out.job.job_id == "job_1"


def test_http_normalizes_direct_image():
    def handler(request):
        return httpx.Response(200, json={"images": [{"url": "/artifacts/x.png", "width": 512, "height": 512,
                                                     "seed": 1, "prompt": "x", "model": "m"}], "mode": "t2i", "model": "m"})
    c = _http_client(handler)
    out = c.generate_image(ImageRequest(prompt="x"))
    assert out.direct is not None
    assert out.direct.images[0].url == "https://api.example.com/artifacts/x.png"


def test_http_unknown_state_preserved():
    def handler(request):
        return httpx.Response(200, json={"job_id": "j", "kind": "image", "status": "weird_state"})
    c = _http_client(handler)
    s = c.get_job("j")
    assert s.status == "weird_state"


def test_http_rejects_untrusted_origin():
    c = _http_client(lambda request: httpx.Response(200))
    c.base = "https://api.example.com"
    try:
        c.download_media("https://evil.example.com/x.png")
        assert False, "devrait lever"
    except GatewayError:
        pass


def test_http_upload_asset_returns_relative_url():
    def handler(request):
        return httpx.Response(200, json={"asset_id": "a1", "url": "/assets/ref.png", "mime_type": "image/png"})
    c = _http_client(handler)
    meta = c.upload_asset("ref.png", b"x")
    # l'URL reste relative : réutilisée telle quelle comme référence de génération
    assert meta.url == "/assets/ref.png"
