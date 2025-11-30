from core.interception import init_proxy
from core.driver import run_driver
from core.shared import state
from core.strategies import Strategies

import argparse
import asyncio
import signal
import sys


async def main(args):
    proxy = init_proxy(scope=args.scope, strategy=args.strategy, fuzz_opts={"model": args.model})

    proxy_task = asyncio.create_task(proxy.run())
    driver_task = asyncio.create_task(run_driver(proxy=proxy))
    try:
        await asyncio.gather(proxy_task, driver_task)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        state.running = False
        proxy.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--strategy", type=Strategies, default=Strategies.BASELINE, choices=list(Strategies), help="Fuzzing strategy to use")
    parser.add_argument("--scope", type=str, default='localhost:5051', help="Scope to intercept (default: localhost:5051)")
    parser.add_argument("-m", "--model", type=str, default='qwen3:8b', help="LLM model to use for fuzzing (default: qwen3:8b)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    asyncio.run(main(args))