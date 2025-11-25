from fastapi import FastAPI
import logging
import httpx
import os

app = FastAPI(title="Consumer Service")
logger = logging.getLogger("consumer")

PRODUCER_URL = os.getenv("PRODUCER_URL")
PROXY_URL = os.getenv("HTTP_PROXY")


async def fetch_data_from_producer(url):
    async with httpx.AsyncClient(proxies=os.getenv("HTTP_PROXY"), timeout=None) as client:
        try:
            resp = await client.get(f"{PRODUCER_URL}{url}")
            return resp
        except Exception as e:
            logger.error(f"Error fetching data from producer: {e}")
            return  None


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "consumer"}


# Scenario 0 - API1:2023 Broken Object Level Authorization
@app.get("/api/v1/admin/view-logs")
async def scenario_0():
    data = await fetch_data_from_producer('/upstream/config/log-settings')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}


# Scenario 1 - API3:2023 Broken Object Property Level Authorization
@app.post("/api/v1/users/sync/{id}")
async def scenario_1(id):
    data = await fetch_data_from_producer(f'/upstream/users/{id}/details')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}


# Scenario 2 - API4:2023 Unrestricted Resource Consumption
@app.post("/api/v1/auth/init")
async def scenario_2():
    data = await fetch_data_from_producer('/upstream/security/policy')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}


# Scenario 3 - API7:2023 Server-Side Request Forgery
@app.get("/api/v1/profile/avatar")
async def scenario_3():
    data = await fetch_data_from_producer('/upstream/user/profile')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}


# Scenario 4 - API8:2023 Security Misconfiguration
@app.get("/api/v1/shop/inventory")
async def scenario_4():
    data = await fetch_data_from_producer('/upstream/inventory/list')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}


# Scenario 5 - API10:2023 Unsafe Consumption of APIs
@app.get("/api/v1/orders/recommendations")
async def scenario_5():
    data = await fetch_data_from_producer('/upstream/analytics/preferences')
    if not data:
        return {"error": "producer not reachable"}
    return {"producer_data": data.json()}