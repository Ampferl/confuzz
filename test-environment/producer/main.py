from fastapi import FastAPI

app = FastAPI(title="Producer Service")

@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "producer"}