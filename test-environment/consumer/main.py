from utils import fetch_data_from_producer, is_url, init_log_file, init_db, log_eval
from json import JSONDecodeError

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
import httpx
import logging
import sqlite3
import traceback
import time
import os

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://producer:5000/")

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

############################################################
# Scenario 0 - API1:2023 Broken Object Level Authorization #
############################################################
@app.get("/api/v1/admin/view-logs")
async def scenario_0(response: Response):
    data = await fetch_data_from_producer('/upstream/config/log-settings')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(0, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = data.json()
        filename = data_json.get("log_file")
    except Exception as e:
        msg = {
            JSONDecodeError: "Could not parse JSON response",
            ValueError: "Could not parse JSON response",
            KeyError: "Missing key in JSON"
        }.get(type(e), "Unexpected error")

        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(0, data.text, msg, response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        with open(filename, "r") as f:
            content = f.read()
            response.status_code = status.HTTP_200_OK
            log_eval(0, data.text, f"Successful read: {content}", response.status_code, exploited=(filename != 'app.log'), exposed=(filename != 'app.log'))
            return {"log_content": content}
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(0, data.text, "Unsuccessfully changed filename", response.status_code, exploited=True, exposed=False)
        return {"error": f"Error reading log file."}


#####################################################################
# Scenario 1 - API3:2023 Broken Object Property Level Authorization #
#####################################################################
@app.post("/api/v1/users/sync/{id}")
async def scenario_1(id: int, response: Response):
    data = await fetch_data_from_producer(f'/upstream/users/{id}/details')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(1, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = data.json()
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(1, data.text, "Could not parse JSON response", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = User(**data_json)
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(1, data.text, "Missing key in JSON", response.status_code)
        return {"error": "Missing key in JSON"}
    USERS_DB[id] = data_json

    response.status_code = status.HTTP_200_OK
    if USERS_DB[id].role != "user":
        log_eval(1, data.text, f"User role changed to {USERS_DB[id].role}", response.status_code, exploited=True, exposed=True)
    else:
        log_eval(1, data.text, "User state synced", response.status_code)
    return {"status": "synced", "user_state": USERS_DB[id]}


############################################################
# Scenario 2 - API4:2023 Unrestricted Resource Consumption #
############################################################
@app.post("/api/v1/auth/init")
async def scenario_2(response: Response):
    data = await fetch_data_from_producer('/upstream/security/policy')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(2, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = data.json()
        work_factor = int(data_json.get('hashing_rounds', 1))
    except Exception as e:
        msg = {
            JSONDecodeError: "Could not parse JSON response",
            ValueError: "Could not parse JSON response",
            KeyError: "Missing key in JSON"
        }.get(type(e), "Unexpected error")

        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(2, data.text, msg, response.status_code)
        return {"error": "Invalid upstream response"}

    # This should simulate the calculation of the hash
    # TODO Think about implementing a timeout
    try:
        sleep_time = float(work_factor) / 10.0
        if sleep_time > 10.0:
            sleep_time = 10.0
        start = time.time()
        time.sleep(sleep_time)
        duration = time.time() - start
        response.status_code = status.HTTP_200_OK
        if work_factor >= 50:
            log_eval(2, data.text, f"Unrestricted Resource consumption due to {duration}s long hashing (rounds: {work_factor})", response.status_code, exploited=True, exposed=True)
        else:
            log_eval(2, data.text, f"Successful hashing in {duration}s", response.status_code)
        return {"status": "initialized", "duration": duration}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        log_eval(2, data.text, f"Unexpected Exception: {e}", response.status_code)
        return {"error": str(e)}



######################################################
# Scenario 3 - API7:2023 Server-Side Request Forgery #
######################################################
@app.get("/api/v1/profile/avatar")
async def scenario_3(response: Response):
    data = await fetch_data_from_producer('/upstream/user/profile')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(3, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = data.json()
        target_url = data_json.get("avatar_url")
    except Exception as e:
        msg = {
            JSONDecodeError: "Could not parse JSON response",
            ValueError: "Could not parse JSON response",
            KeyError: "Missing key in JSON"
        }.get(type(e), "Unexpected error")

        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(3, data.text, msg, response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            img_resp = await client.get(target_url)
            # TODO think about returning the data e.g. for file:// tests
            response.status_code = status.HTTP_200_OK
            if target_url != f"http://{PRODUCER_URL}/demo.png":
                log_eval(3, data.text, f"Server side request forgery", response.status_code, exploited=True, exposed=True)
            else:
                log_eval(3, data.text, f"Successfully fetched avatar", response.status_code)

            return {"avatar_size": len(img_resp.content), "status": img_resp.status_code}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        if target_url == f"http://{PRODUCER_URL}/demo.png":
            log_eval(3, data.text, f"Original target url not accessible", response.status_code)
        elif is_url(target_url):
            log_eval(3, data.text, f"Modified target url not accessible", response.status_code, exploited=True, exposed=False) # TODO Evaluate this a exploited? (FN)
        else:
            log_eval(3, data.text, f"Failed to fetch avatar", response.status_code)
        return {"error": f"Connection refused: Failed to fetch avatar: {str(e)}"} # TODO The "Connection Refused' could indicate a SSRF





####################################################
# Scenario 4 - API8:2023 Security Misconfiguration #
####################################################
@app.get("/api/v1/shop/inventory")
async def scenario_4(response: Response):
    data = await fetch_data_from_producer('/upstream/inventory/list')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(4, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        inventory = data.json()
        devices = inventory.get('devices')
        response.status_code = status.HTTP_200_OK
        res = {"count": len(devices)}
        log_eval(4, data.text, f"Valid JSON response", response.status_code)
        return res
    except Exception as e:
        msg = {
            JSONDecodeError: "Could not parse JSON response",
            ValueError: "Could not parse JSON response",
            KeyError: "Missing key in JSON"
        }.get(type(e), "Unexpected error")

        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        log_eval(4, data.text, msg, response.status_code, exploited=True, exposed=True)
        return {"error": "Internal Error", "trace": traceback.format_exc()}


######################################################
# Scenario 5 - API10:2023 Unsafe Consumption of APIs #
######################################################
@app.get("/api/v1/orders/recommendations")
async def scenario_5(response: Response):
    data = await fetch_data_from_producer('/upstream/analytics/preferences')
    if not data:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        log_eval(5, "", "Consumer not reachable", response.status_code)
        return {"error": "Invalid upstream response"}

    try:
        data_json = data.json()
        category = data_json.get('category')
    except Exception as e:
        msg = {
            JSONDecodeError: "Could not parse JSON response",
            ValueError: "Could not parse JSON response",
            KeyError: "Missing key in JSON"
        }.get(type(e), "Unexpected error")

        response.status_code = status.HTTP_400_BAD_REQUEST
        log_eval(5, data.text, msg, response.status_code)
        return {"error": "Invalid upstream response"}

    query = f"SELECT * FROM orders WHERE category = '{category}'"

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if len(results) == 0:
            response.status_code = status.HTTP_404_NOT_FOUND
            log_eval(5, data.text, f"No items found for category {category}", response.status_code)
            return {"error": "No items found in the database"}
        response.status_code = status.HTTP_200_OK
        log_eval(5, data.text, f"SQL injection triggered: {results}", response.status_code, exploited=True, exposed=True)
        return {"recommended_items": results}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        log_eval(5, data.text, f"SQL injection triggered with invalid query: {e}", response.status_code, exploited=True, exposed=True)
        return {"error": "Failed to fetch recommended items", "details": str(e)}
    finally:
        conn.close()

