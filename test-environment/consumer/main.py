from utils import fetch_data_from_producer, init_log_file

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os
import sqlite3
import traceback
import time

app = FastAPI(title="Consumer Service")
logger = logging.getLogger("consumer")

# In-memory DB for Scenario 1
USERS_DB = {}



@app.on_event("startup")
async def startup_event():
    init_log_file()


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "consumer"}


# Scenario 0 - API1:2023 Broken Object Level Authorization
@app.get("/api/v1/admin/view-logs")
async def scenario_0():
    data = await fetch_data_from_producer('/upstream/config/log-settings')
    if not data:
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
    except:
        return {"error": "Invalid upstream response"}

    filename = data.get("log_file")

    try:
        with open(filename, "r") as f:
            return {"log_content": f.read()}
    except:
        return {"error": f"Error reading log file."}


# Scenario 1 - API3:2023 Broken Object Property Level Authorization
@app.post("/api/v1/users/sync/{id}")
async def scenario_1(id: int):
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