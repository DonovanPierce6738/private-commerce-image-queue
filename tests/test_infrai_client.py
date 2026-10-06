import base64
import json

import httpx

from ecommerce_image_worker.infrai_client import InfraiImageClient


async def test_upload_sends_json_file_and_filename() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "data": {"id": "image-1"}})

    client = InfraiImageClient("test-key", transport=httpx.MockTransport(respond))
    try:
        assert await client.upload(b"image-bytes", "product.jpg", "upload-1") == {"id": "image-1"}
    finally:
        await client.close()

    request = requests[0]
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Idempotency-Key"] == "upload-1"
    assert json.loads(request.content) == {
        "file": base64.b64encode(b"image-bytes").decode("ascii"),
        "filename": "product.jpg",
    }
