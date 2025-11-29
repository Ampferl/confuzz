from core.interception import init_proxy
from core.driver import run_driver
from core.shared import state
from core.strategies import Strategies

import asyncio
import signal
import sys


SCOPE='localhost:5051'
STRATEGY = Strategies.BASELINE
OPTS = {
    "feedback_log_file": "../scripts/feedback.json",
    "fuzz_timeout": 10,
}

async def main():
    proxy = init_proxy(scope=SCOPE, strategy=STRATEGY, fuzz_opts=OPTS)

    proxy_task = asyncio.create_task(proxy.run())
    driver_task = asyncio.create_task(run_driver())
    try:
        await asyncio.gather(proxy_task, driver_task)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        state.running = False
        proxy.shutdown()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    asyncio.run(main())