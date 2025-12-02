from mitmproxy import http, options
from mitmproxy.tools import dump

from utils import in_scope, colorize_changes
from core.strategies import Strategies
from core.shared import state
from core.strategies.custom_baseline.fuzzer import CustomBaselineFuzzer
from core.strategies.baseline.fuzzer import BaselineFuzzer
from core.strategies.llm.fuzzer import LLMGeneratorFuzzer, LLMMutatorFuzzer

import asyncio
import logging
import json

logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("proxy")

# Disable logs from mitmproxy
logging.getLogger("mitmproxy").setLevel(logging.CRITICAL + 10)
logging.getLogger("mitmproxy").propagate = False


class InterceptionAddon:
    def __init__(self, scope: str, strategy: Strategies, opts: dict|None = None) -> None:
        self.scope = scope
        self.strategy = strategy
        self.fuzzer = None
        self.opts = opts
        self.feedback_data = []
        self._init_fuzzer(strategy)


    def _init_fuzzer(self, strategy: Strategies):
        match strategy:
            case Strategies.CUSTOM_BASELINE:
                self.fuzzer = CustomBaselineFuzzer()
                logger.info(f"[i] Custom Baseline Fuzzer initialized")
            case Strategies.BASELINE:
                self.fuzzer = BaselineFuzzer()
                logger.info(f"[i] Baseline Fuzzer initialized")
            case Strategies.LLM_GENERATION:
                self.fuzzer = LLMGeneratorFuzzer(self.opts.get("model"))
                logger.info(f"[i] LLM generation-based Fuzzer initialized")
            case Strategies.LLM_MUTATION:
                self.fuzzer = LLMMutatorFuzzer(self.opts.get("model"))
                logger.info(f"[i] LLM mutation-based Fuzzer initialized")


    def fetch_feedback_queue(self):
        try:
            while not state.feedback_queue.empty():
                self.feedback_data[-1]["feedback"].append(state.feedback_queue.get_nowait())
        except asyncio.QueueEmpty: pass

    def request(self, flow: http.HTTPFlow) -> None:
        if in_scope("intercept.confuzz", flow):
            state.ssrf_detected = True


    def response(self, flow: http.HTTPFlow) -> None:
        if in_scope(self.scope, flow):
            logger.info(f"(<-) Intercepted Response: {flow.response.status_code}")

            original_body = flow.response.text
            print(f"[ORIG]: {original_body}")
            self.fetch_feedback_queue()
            # Analyze Feedback?

            mutated_body = self.fuzzer.fuzz(original_body, feedback=None if len(self.feedback_data) == 0 else self.feedback_data, request=flow.request.path, opts=self.opts)
            print(f"[FUZZ]: {colorize_changes(original_body, mutated_body, mode='changes')}")
            flow.response.text = mutated_body
            logger.info(f"[{self.strategy.name}]: {flow.response.text}")
            self.feedback_data.append({
                "path": flow.request.path,
                "response": original_body,
                "fuzzed": mutated_body,
                "feedback": []
            })

            state.fuzz_finished = asyncio.get_event_loop().time()


def init_proxy(scope: str, strategy: Strategies, fuzz_opts: dict|None = None):
    opts = options.Options(listen_host='0.0.0.0', listen_port=8080, ssl_insecure=True)
    master = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    interception_addon = InterceptionAddon(scope=scope, strategy=strategy, opts=fuzz_opts)
    master.addons.add(interception_addon)
    return master