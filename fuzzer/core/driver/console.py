from core.shared import state
from core.driver.stats import stats_tracker
from core.driver.config import SCENARIOS
from core.driver.trigger import run_auto_mode, run_scenario_loop
import asyncio


async def run_driver(proxy):
    print("Driver ready. Type 'help' for commands.")
    while state.running:
        try:
            inp = await asyncio.to_thread(input, "$ ")
            parts = inp.strip().split()
            if not parts: continue

            cmd = parts[0]

            if cmd == "exit":
                proxy.shutdown()
                state.running = False
                break
            elif cmd == "stats":
                stats_tracker.print_stats()
            elif cmd == "auto":
                asyncio.create_task(run_auto_mode())
            elif cmd == "fuzz":
                if len(parts) < 2:
                    print("Usage: fuzz <id>")
                    continue
                try:
                    sid = int(parts[1])
                    if sid not in SCENARIOS:
                        print("Invalid Scenario ID")
                        continue
                    asyncio.create_task(run_scenario_loop(sid))
                except ValueError:
                    print("Invalid ID")
            elif cmd == "help":
                print("Commands:")
                print("  auto       - Run all scenarios sequentially until exploited")
                print("  fuzz <id>  - Fuzz specific scenario ID until exploited")
                print("  stats      - Show statistics")
                print("  exit       - Stop Fuzzer and Proxy")
            else:
                print("Unknown command.")
        except Exception as e:
            print(f"Error reading input: {e}")
