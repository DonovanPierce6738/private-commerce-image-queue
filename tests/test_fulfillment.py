from ecommerce_image_worker.models import CheckoutOrder, OrderState, ProductImage
from ecommerce_image_worker.queue_worker import QueueWorker


class RecordingPipeline:
    def __init__(self) -> None:
        self.request_ids: list[str] = []

    async def upload(self, content: bytes, filename: str, request_id: str) -> dict:
        self.request_ids.append(request_id)
        return {"id": f"uploaded-{filename}"}

    async def smart_crop(self, image: str, aspect: str, request_id: str) -> dict:
        self.request_ids.append(request_id)
        return {"id": f"cropped-{image}"}

    async def compress(self, image: str, request_id: str) -> dict:
        self.request_ids.append(request_id)
        return {"id": f"compressed-{image}"}


async def test_complete_image_batch_fulfills_order_and_issues_receipt() -> None:
    pipeline = RecordingPipeline()

    async def private_catalog_fetch(url: str) -> bytes:
        return b"catalog-image"

    worker = QueueWorker(pipeline, private_catalog_fetch)
    order = CheckoutOrder(
        order_id="ord-2048",
        customer_id="customer-17",
        images=[
            ProductImage(sku="bandage-blue", source_url="https://images.example/bandage.jpg"),
            ProductImage(sku="thermometer", source_url="https://images.example/thermometer.jpg"),
        ],
    )

    result = await worker.process_order(order)

    assert result.state is OrderState.FULFILLED
    assert result.receipt is not None
    assert result.receipt.processed_images == 2
    assert result.customer_update.state is OrderState.FULFILLED
    assert pipeline.request_ids == [
        "ord-2048:bandage-blue:upload",
        "ord-2048:bandage-blue:crop",
        "ord-2048:bandage-blue:compress",
        "ord-2048:thermometer:upload",
        "ord-2048:thermometer:crop",
        "ord-2048:thermometer:compress",
    ]

