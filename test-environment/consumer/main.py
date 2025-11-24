from fastapi import FastAPI

app = FastAPI(title="Consumer Service")

@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "consumer"}