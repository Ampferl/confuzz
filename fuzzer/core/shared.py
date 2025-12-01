import asyncio

class SharedState:
    def __init__(self):
        # Pass feedback through queue from Driver to Proxy
        self.feedback_queue = asyncio.Queue()
        # Start timeout countdown if fuzzer quits
        self.fuzz_finished = None
        self.running = True
        self.ssrf_detected = False
        self.opts = {
            "max_requests": 1000,
        }

        self.stats = {
            "requests": 0
        }


state = SharedState()
