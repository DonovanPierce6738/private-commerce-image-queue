import asyncio

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiError, InfraiImageClient
from .models import BatchRequest, BatchResult
from .queue_worker import QueueWorker

app = FastAPI(title="Private commerce image queue")


@app.post("/orders/batch", response_model=BatchResult)
async def process_batch(batch: BatchRequest) -> BatchResult:
    client = InfraiImageClient.from_environment()
    worker = QueueWorker(client)
    try:
        results = await asyncio.gather(*(worker.process_order(order) for order in batch.orders))
        return BatchResult(results=results)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc
    finally:
        await client.close()

