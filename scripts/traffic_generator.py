import requests
import time
import json
import logging
import argparse

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

FEEDBACK_DATA = []

def run_scenario(scenario_id, duration_seconds=60, delay=1.0):
    target = SCENARIOS.get(scenario_id)
    if not target:
        logger.error(f"Unknown scenario ID: {scenario_id}")
        return

    logger.info(f"[*] Starting Fuzzing Loop for {scenario_id} ({duration_seconds}s)...")

    start_time = time.time()
    count = 0

    while (time.time() - start_time) < duration_seconds:
        count += 1
        full_url = f"{CONSUMER_HOST}{target['url']}"

        try:
            match target['method']:
                case "GET":
                    resp = requests.get(full_url, timeout=5)
                case "POST":
                    resp = requests.post(full_url, json={}, timeout=5)

            FEEDBACK_DATA.append({
                    "scenario": scenario_id,
                    "path": target['url'],
                    "status_code": resp.status_code,
                    "body": resp.text
                })
            with open("feedback.json", "w") as f:
                json.dump(FEEDBACK_DATA, f)

            logger.info(f"-> Triggered iteration {count}")

        except requests.exceptions.Timeout:
            logger.warning(f"[!] Consumer timed out (Potential DoS or Latency!)")
        except Exception as e:
            logger.error(f"[!] Driver Error: {e}")

        time.sleep(delay)

    logger.info(f"[*] Finished {scenario_id}. Triggered {count} requests.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, help="Specific scenario ID (0-5) to run")
    parser.add_argument("--all", action="store_true", help="Run all scenarios sequentially")
    parser.add_argument("--duration", type=int, default=60, help="Duration per scenario in seconds")

    args = parser.parse_args()

    if args.all:
        for i in range(6):
            run_scenario(i, args.duration)
    elif args.scenario is not None:
        run_scenario(args.scenario, args.duration)
    else:
        print("Please specify --scenario <id> or --all")