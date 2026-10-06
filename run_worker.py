import uvicorn


if __name__ == "__main__":
    uvicorn.run("ecommerce_image_worker.service:app", host="127.0.0.1", port=8000)

