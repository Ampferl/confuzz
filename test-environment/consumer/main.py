from utils import fetch_data_from_producer, init_log_file, init_db

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
import httpx
import logging
import os
import sqlite3
import traceback
import time

app = FastAPI(title="Consumer Service")
logger = logging.getLogger("consumer")

# In-memory DB for Scenario 1
USERS_DB = {}


class User(BaseModel):
    username: str
    email: str
    role: str = "user"


@app.on_event("startup")
async def startup_event():
    init_log_file()
    init_db()


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "consumer"}


# Scenario 0 - API1:2023 Broken Object Level Authorization
@app.get("/api/v1/admin/view-logs")
async def scenario_0(response: Response):
    data = await fetch_data_from_producer('/upstream/config/log-settings')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
        filename = data.get("log_file")
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        logger.error(f"Invalid upstream response: {response.status_code}")
        return {"error": "Invalid upstream response"}

    try:
        with open(filename, "r") as f:
            return {"log_content": f.read()}
    except:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": f"Error reading log file."}


# Scenario 1 - API3:2023 Broken Object Property Level Authorization
@app.post("/api/v1/users/sync/{id}")
async def scenario_1(id: int, response: Response):
    data = await fetch_data_from_producer(f'/upstream/users/{id}/details')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Invalid upstream response"}

    data = User(**data)
    USERS_DB[id] = data

    return {"status": "synced", "user_state": USERS_DB[id]}


# Scenario 2 - API4:2023 Unrestricted Resource Consumption
@app.post("/api/v1/auth/init")
async def scenario_2(response: Response):
    data = await fetch_data_from_producer('/upstream/security/policy')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
        work_factor = data.get('hashing_rounds', 1)
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Invalid upstream response"}

    # This should simulate the calculation of the hash
    try:
        start = time.time()
        time.sleep(float(work_factor) / 10.0)
        duration = time.time() - start
        return {"status": "initialized", "duration": duration}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": str(e)}



# Scenario 3 - API7:2023 Server-Side Request Forgery
@app.get("/api/v1/profile/avatar")
async def scenario_3(response: Response):
    data = await fetch_data_from_producer('/upstream/user/profile')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
        target_url = data.get("avatar_url")
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Invalid upstream response"}

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            img_resp = await client.get(target_url)
            return {"avatar_size": len(img_resp.content), "status": img_resp.status_code}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": f"Failed to fetch avatar: {str(e)}"}



# Scenario 4 - API8:2023 Security Misconfiguration
@app.get("/api/v1/shop/inventory")
async def scenario_4(response: Response):
    data = await fetch_data_from_producer('/upstream/inventory/list')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        inventory = data.json()
        return {"count": len(inventory['devices'])}
    except Exception:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "Internal Error", "trace": traceback.format_exc()}


# Scenario 5 - API10:2023 Unsafe Consumption of APIs
@app.get("/api/v1/orders/recommendations")
async def scenario_5(response: Response):
    data = await fetch_data_from_producer('/upstream/analytics/preferences')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {"error": "Invalid upstream response"}

    try:
        data = data.json()
        category = data.get('category')
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Invalid upstream response"}

    query = f"SELECT * FROM orders WHERE category = '{category}'"

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if len(results) == 0:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": "No items found in the database"}
        return {"recommended_items": results}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"error": "Failed to fetch recommended items", "details": str(e)}
    finally:
        conn.close()

