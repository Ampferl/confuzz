from fastapi import FastAPI
import os

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://producer:5000/")

app = FastAPI(title="Producer Service")

@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "producer"}


@app.get("/demo.png")
async def avatar():
    return {"avatar": "demo"}


# Scenario 0 - API1:2023 Broken Object Level Authorization
@app.get("/upstream/config/log-settings")
async def scenario_0():
    return {"log_file": "app.log"}


# Scenario 1 - API3:2023 Broken Object Property Level Authorization
@app.get("/upstream/users/{id}/details")
async def scenario_1(id: int):
    return {"username": f"user_{id}", "email": f"user{id}@example.com"}


# Scenario 2 - API4:2023 Unrestricted Resource Consumption
@app.get("/upstream/security/policy")
async def scenario_2():
    return {"hashing_algorithm": "custom_hash", "hashing_rounds": 10}


# Scenario 3 - API7:2023 Server-Side Request Forgery
@app.get("/upstream/user/profile")
async def scenario_3():
    # TODO Change this to a URL from the producer?
    return {"avatar_url": f"http://{PRODUCER_URL}/demo.png"}


# Scenario 4 - API8:2023 Security Misconfiguration
@app.get("/upstream/inventory/list")
async def scenario_4():
    return {"devices": ["phone", "laptop", "server"]}


# Scenario 5 - API10:2023 Unsafe Consumption of APIs
@app.get("/upstream/analytics/preferences")
async def scenario_5():
    return {"category": "tools"}

