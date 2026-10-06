from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class OrderState(StrEnum):
    CHECKED_OUT = "checked_out"
    FULFILLED = "fulfilled"


class ProductImage(BaseModel):
    sku: str = Field(min_length=1)
    source_url: HttpUrl


class CheckoutOrder(BaseModel):
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    images: list[ProductImage] = Field(min_length=1, max_length=50)


class ProcessedImage(BaseModel):
    sku: str
    image_id: str


class Receipt(BaseModel):
    order_id: str
    processed_images: int
    status: str = "issued"


class CustomerOrderUpdate(BaseModel):
    customer_id: str
    order_id: str
    state: OrderState


class FulfillmentResult(BaseModel):
    order_id: str
    state: OrderState
    images: list[ProcessedImage]
    receipt: Receipt | None
    customer_update: CustomerOrderUpdate


class BatchRequest(BaseModel):
    orders: list[CheckoutOrder] = Field(min_length=1, max_length=25)


class BatchResult(BaseModel):
    results: list[FulfillmentResult]

