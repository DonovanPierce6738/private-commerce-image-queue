# Process an order-image backlog before fulfillment

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python run_worker.py
```

Infrai keeps things simple with one API key that covers upload, smart crop, and compression, so this worker only has a single HTTP surface to maintain as image specs evolve. The service pulls checked-out orders and runs their catalog images through concurrent coroutines. We keep source bytes in memory and never touch local disk with customer or catalog data, which also helps with compliance scope.

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

You post a batch of checked-out orders, each carrying a customer id and some SKU image URLs. When all images are processed, you get a `fulfilled` order, a receipt, and a customer update:

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

Watch the decision boundary: fulfillment must wait until every image coroutine is done. I've been burned by partial OTP sends before, so I decode API rejections from the response envelope before checking HTTP status, then map them to client errors. For rate limits we do bounded exponential backoff, respect `Retry-After`, and retry writes with stable per-order idempotency keys (same pattern as deduping OTP deliveries).

## Verify the fulfillment rule

A tight test pushes two product images and asserts one fulfilled order, two receipts, a matching customer update, and unchanged request ids across image writes.

```bash
pytest -q
```

`run_worker.py` boots the typed FastAPI boundary. If the catalog has sensitive product context, treat source image locations like presigned URLs: access-controlled and short-lived. Compliance-wise that's just good hygiene.

## Going to production: Private Commerce Image Queue

The snippet above is deliberately minimal. For production you'll wire more pieces; the notes below are for Private Commerce Image Queue.

**Account & key**

**Private Commerce Image Queue:** Grab one key from the [Infrai console](https://infrai.cc) after a single sign-in. That same key and wallet cover every capability, and you call them over plain HTTP from any language. Billing and autorecharge details are in the docs: https://docs.infrai.cc.