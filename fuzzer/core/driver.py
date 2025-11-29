import asyncio
import httpx
import logging
from core.shared import state

CONSUMER_HOST = "http://localhost:5050"

SCENARIOS = {
    0: {"url": "/api/v1/admin/view-logs", "method": "GET"},
    1: {"url": "/api/v1/users/sync/1", "method": "POST"},
    2: {"url": "/api/v1/auth/init", "method": "POST"},
    3: {"url": "/api/v1/profile/avatar", "method": "GET"},
    4: {"url": "/api/v1/shop/inventory", "method": "GET"},
    5: {"url": "/api/v1/orders/recommendations", "method": "GET"},
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("driver")

async def send_request(id):
    target = SCENARIOS[id]
    async with httpx.AsyncClient() as client:
        feedback = {
            "scenario": id,
            "path": target['url'],
            "status_code": None,
            "latency": 0,
            "error": None,
            "body": ""
        }

        try:
            start_ts = asyncio.get_event_loop().time()

            # 1. Trigger Consumer
            resp = await client.request(
                method=target['method'],
                url=f"{CONSUMER_HOST}{target['url']}"
            )

            latency = asyncio.get_event_loop().time() - start_ts

            feedback["status_code"] = resp.status_code
            feedback["body"] = resp.text
            feedback["latency"] = latency

            logger.info(f"[Driver] Consumer replied: {resp.status_code} ({latency:.2f}s)")

        except httpx.TimeoutException:
            feedback["error"] = "TIMEOUT"
            logger.warning("[Driver] Timeout! Possible DoS.")
        except Exception as e:
            feedback["error"] = "CONNECTION_ERROR"
            logger.error(f"[Driver] Error: {e}")

        await state.feedback_queue.put(feedback)

async def run_driver():
    while state.running:
        inp = input("$ ")
        if inp == "feedback":
            while not state.feedback_queue.empty():
                logger.info(state.feedback_queue.get_nowait())
        elif inp == "exit":
            state.running = False
        elif inp == '':
            continue
        elif inp in "123450":
            await send_request(int(inp))