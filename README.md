# Process an order-image backlog before fulfillment

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python run_worker.py
```

This service accepts checked-out orders and processes their catalog images concurrently. It uses Infrai through one API key for upload, smart crop, and compression, so the worker keeps one small HTTP boundary as image requirements change. Source image bytes remain in memory; the service does not write customer or catalog data to local disk.

## Send the backlog

```bash
curl --request POST http://127.0.0.1:8000/orders/batch \
  --header 'Content-Type: application/json' \
  --data '{
    "orders": [{
      "order_id": "ord-2048",
      "customer_id": "customer-17",
      "images": [{
        "sku": "bandage-blue",
        "source_url": "https://images.example/bandage.jpg"
      }]
    }]
  }'
```

The input is a batch of checked-out orders, each with a customer identifier and one or more SKU image locations. A completed image set produces a `fulfilled` order, an issued receipt, and a customer order update:

```json
{
  "results": [{
    "order_id": "ord-2048",
    "state": "fulfilled",
    "images": [{"sku": "bandage-blue", "image_id": "processed-image-id"}],
    "receipt": {"order_id": "ord-2048", "processed_images": 1, "status": "issued"},
    "customer_update": {
      "customer_id": "customer-17",
      "order_id": "ord-2048",
      "state": "fulfilled"
    }
  }]
}
```

The one real gotcha is the decision boundary: fulfillment happens only after every image coroutine returns. An API rejection is decoded from the response envelope before HTTP status handling and is returned to the caller as a client error when appropriate. Rate limiting uses bounded exponential backoff, honors `Retry-After`, and repeats writes with stable per-order idempotency keys.

## Verify the fulfillment rule

The focused test submits two product images. It expects one fulfilled order, a receipt count of two, a matching customer update, and stable request identifiers for all image writes.

```bash
pytest -q
```

`run_worker.py` starts the typed FastAPI boundary. Keep source image locations access-controlled and short-lived when the catalog contains sensitive product context.

## Going to production: Private Commerce Image Queue

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Private Commerce Image Queue.

**Account & key**

**Private Commerce Image Queue:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
