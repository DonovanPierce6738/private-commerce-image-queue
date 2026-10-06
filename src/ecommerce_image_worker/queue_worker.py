import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from .models import (
    CheckoutOrder,
    CustomerOrderUpdate,
    FulfillmentResult,
    OrderState,
    ProcessedImage,
    Receipt,
)


class ImagePipeline(Protocol):
    async def upload(self, content: bytes, filename: str, request_id: str) -> dict:
        raise RuntimeError

    async def smart_crop(self, image: str, aspect: str, request_id: str) -> dict:
        raise RuntimeError

    async def compress(self, image: str, request_id: str) -> dict:
        raise RuntimeError


FetchImage = Callable[[str], Awaitable[bytes]]


async def fetch_source_image(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method="GET", url=url)
        response.raise_for_status()
        return response.content


class QueueWorker:
    def __init__(self, pipeline: ImagePipeline, fetch_image: FetchImage = fetch_source_image):
        self.pipeline = pipeline
        self.fetch_image = fetch_image

    async def process_order(self, order: CheckoutOrder) -> FulfillmentResult:
        processed = await asyncio.gather(
            *(self._process_image(order.order_id, item.sku, str(item.source_url)) for item in order.images)
        )
        state = OrderState.FULFILLED
        return FulfillmentResult(
            order_id=order.order_id,
            state=state,
            images=processed,
            receipt=Receipt(order_id=order.order_id, processed_images=len(processed)),
            customer_update=CustomerOrderUpdate(
                customer_id=order.customer_id,
                order_id=order.order_id,
                state=state,
            ),
        )

    async def _process_image(self, order_id: str, sku: str, source_url: str) -> ProcessedImage:
        content = await self.fetch_image(source_url)
        uploaded = await self.pipeline.upload(content, f"{sku}.jpg", f"{order_id}:{sku}:upload")
        cropped = await self.pipeline.smart_crop(
            str(uploaded["id"]), "1:1", f"{order_id}:{sku}:crop"
        )
        compressed = await self.pipeline.compress(
            str(cropped["id"]), f"{order_id}:{sku}:compress"
        )
        return ProcessedImage(sku=sku, image_id=str(compressed["id"]))
