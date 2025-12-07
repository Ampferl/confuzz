from core.interception import init_proxy
from core.driver.console import run_driver
from core.shared import state
from utils import init_logger
from core.strategies import Strategies
from core.strategies.llm.connector import LLModels

import argparse
import asyncio
import signal
import sys


async def main(args):
    init_logger(strategy=args.strategy)

    state.opts["max_requests"] = args.max_requests
    state.opts["list"] = args.list
    state.opts["attack_threshold"] = args.threshold
    state.opts["rate_limit"] = args.rate_limit
    state.opts["debug"] = args.debug

    proxy = init_proxy(scope=args.scope, strategy=args.strategy, fuzz_opts={"model": args.model, "think": args.think, "temperature": args.temperature})
    try:
        proxy_task = asyncio.create_task(proxy.run())
        driver_task = asyncio.create_task(run_driver(proxy=proxy))
        await asyncio.gather(proxy_task, driver_task)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        # THIS HAS TO BE EXECUTED IF SIGINT!
        state.running = False
        proxy.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=Strategies, default=Strategies.BASELINE, choices=list(Strategies), help="Fuzzing strategy to use")
    parser.add_argument("--scope", type=str, default='localhost:5051', help="Scope to intercept (default: localhost:5051)")
    parser.add_argument("--model", type=LLModels, default=LLModels.QWEN3, choices=list(LLModels), help="LLM model to use for fuzzing (default: qwen3:8b)")
    parser.add_argument("--think", action="store_true", help="Enable thinking on the LLM")
    parser.add_argument("--temperature", type=float, default=0.7, choices=[i/10 for i in range(1, 13, 1)], help="Change the temperature of the LLM")
    parser.add_argument("--max-requests", type=int, default=1000, help="Maximum number of requests to send to the consumer per scenario (default: 1000)")
    parser.add_argument("--threshold", type=int, default=5, help="Number of attempts to generate a new vector for a given scenario (default: 5)")
    parser.add_argument("--rate-limit", type=int, default=0, help="Specify how many seconds to sleep between requests (default: 0, no rate limit)")
    parser.add_argument("--list", type=str, default="custom", choices=["custom", "blns"], help="List of strings to use for baseline fuzzing")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debugging")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    asyncio.run(main(args))
