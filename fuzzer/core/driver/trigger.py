from datetime import datetime

from core.driver.config import SCENARIOS, CONSUMER_HOST
from core.driver.stats import stats_tracker
from utils import RED, RESET, GREEN, YELLOW
from core.shared import state
import logging
import asyncio
import httpx

logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("driver")


def detect_exploit(feedback: dict) -> bool:
    if feedback["error"] in ["SSRF", "TIMEOUT"]:
        return True
    scenario_result = SCENARIOS.get(feedback.get("scenario")).get("expected_result")
    if scenario_result != "" and scenario_result in feedback["body"]:
        return True
    if feedback["status_code"] == 500:
        return True
    return False


async def send_request(id):
    target = SCENARIOS[id]
    stats_tracker.start_scenario(id)

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

            resp = await client.request(
                method=target['method'],
                url=f"{CONSUMER_HOST}{target['url']}"
            )

            state.stats["requests"] += 1
            stats_tracker.total_requests += 1
            stats_tracker.scenario_stats[id]["requests"] += 1

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
            if state.ssrf_detected:
                feedback["error"] = "SSRF"
                state.ssrf_detected = False
            feedback["latency"] = {
                "total": latency,
                "consumer": consumer_latency,
                "fuzzer": llm_latency
            }


        except httpx.TimeoutException:
            feedback["error"] = "TIMEOUT"
            logger.warning(f"[Driver] Timeout on S{id}! Possible DoS.")
        except Exception as e:
            feedback["error"] = "CONNECTION_ERROR"
            logger.error(f"[Driver] Error: {e}")

        if detect_exploit(feedback):
            print(f"{GREEN}[!!!] VULNERABILITY/BUG FOUND FOR SCENARIO {id}{RESET}")
            stats_tracker.mark_exploited(id)
            await state.feedback_queue.put(feedback)
            return True

        await state.feedback_queue.put(feedback)
        return False


async def run_scenario_loop(id):
    print(f"[*] Starting Fuzzing Campaign for Scenario {id}...")
    while state.running:
        if stats_tracker.scenario_stats[id]["exploited"]:
            print(f"{GREEN}[+] Scenario {id} Exploited! Stopping.{RESET}")
            break

        is_exploited = await send_request(id)
        if is_exploited:
            break

        if stats_tracker.scenario_stats[id]["requests"] >= state.opts.get("max_requests", 1000):
            print(f"{YELLOW}[!] Scenario {id} Exhausted! Stopping.{RESET}")
            break

        await asyncio.sleep(state.opts.get("rate_limit", 0))


async def run_auto_mode():
    print(f"[*] Starting AUTO MODE (All Scenarios)...")
    stats_tracker.start_time = datetime.now()
    for i in range(6):
        if not state.running: break
        await run_scenario_loop(i)

    print("[*] Auto Mode Finished.")
    stats_tracker.print_stats()