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


logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("driver")


# TODO Refactor
async def send_request(id):
    target = SCENARIOS[id]
    async with httpx.AsyncClient(timeout=None) as client:
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
            print(f"testing: 'Scenario {id}' -> {target['url']}")
            # 1. Trigger Consumer
            resp = await client.request(
                method=target['method'],
                url=f"{CONSUMER_HOST}{target['url']}"
            )
            state.stats["requests"] += 1

            latency = asyncio.get_event_loop().time() - start_ts

            consumer_latency = asyncio.get_event_loop().time() - state.fuzz_finished
            llm_latency = latency - consumer_latency
            if consumer_latency > 5:
                feedback["error"] = "TIMEOUT"
                logger.warning(f"[Driver] Consumer latency: {consumer_latency}")
                logger.warning(f"[Driver] Total latency: {latency}")
            else:
                feedback["status_code"] = resp.status_code
                feedback["body"] = resp.text
                print(f"[FEED]: {resp.text}")
            feedback["latency"] = {
                "total": latency,
                "consumer": consumer_latency,
                "fuzzer": llm_latency
            }
            print(f"[STATS] Latency\n- Total: {latency}\n- Consumer: {consumer_latency}\n- Fuzzer: {llm_latency}")

            logger.info(f"[Driver] Consumer Feedback: {feedback}")

        except httpx.TimeoutException:
            feedback["error"] = "TIMEOUT"
            logger.warning("[Driver] Timeout! Possible DoS.")
        except Exception as e:
            feedback["error"] = "CONNECTION_ERROR"
            logger.error(f"[Driver] Error: {e}")

        await state.feedback_queue.put(feedback)


async def run_driver(proxy):
    while state.running:
        # TODO
        # - Set options ?
        # - trigger scenarios/campaigns
        # - auto mode for evaluation
        # - stats
        inp = input("$ ")
        if inp == "exit":
            proxy.shutdown()
            state.running = False
        elif inp == '':
            continue
        elif inp == "stats":
            print("== Statistics ==")
            print(f"Total requests: {state.stats['requests']}")
        elif inp in "123450":
            await send_request(int(inp))
