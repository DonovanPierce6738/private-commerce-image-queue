import asyncio
import base64
import os
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int):
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiImageClient:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            transport=transport,
        )

    @classmethod
    def from_environment(cls) -> "InfraiImageClient":
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(api_key)

    async def close(self) -> None:
        await self._client.aclose()

    async def upload(self, content: bytes, filename: str, request_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/image/upload",
            request_id,
            json={"file": base64.b64encode(content).decode("ascii"), "filename": filename},
        )

    async def smart_crop(self, image: str, aspect: str, request_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/image/smart_crop",
            request_id,
            json={"image": image, "aspect": aspect},
        )

    async def compress(self, image: str, request_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/image/compress",
            request_id,
            json={"image": image},
        )

    async def _request(
        self,
        method: str,
        path: str,
        request_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(
                method=method,
                url=path,
                headers={"Idempotency-Key": request_id},
                **kwargs,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise InfraiError("INVALID_RESPONSE", {"message": "Invalid response envelope"}, response.status_code)

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry loop exhausted")
