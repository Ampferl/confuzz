import asyncio

class SharedState:
    def __init__(self):
        # Pass feedback through queue from Driver to Proxy
        self.feedback_queue = asyncio.Queue()
        # Start timeout countdown if fuzzer quits
        self.running = True


state = SharedState()
