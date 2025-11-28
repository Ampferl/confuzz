from core.interception import init_proxy

from utils import Strategies

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
    try:
        await proxy.run()
    except KeyboardInterrupt:
        proxy.shutdown()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    asyncio.run(main())