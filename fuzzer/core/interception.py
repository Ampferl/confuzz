from mitmproxy import http, options
from mitmproxy.tools import dump

from utils import in_scope, Strategies
from core.baseline.fuzzer import BaselineFuzzer

import logging
import json

logging.basicConfig(level=logging.INFO)
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
        self.feedback_data = None

        match strategy:
            case Strategies.BASELINE:
                self.fuzzer = BaselineFuzzer()
                logger.info(f"[i] Baseline Fuzzer initialized")
            case Strategies.LLM_GENERATION:
                logger.info(f"[i] LLM generation-based Fuzzer initialized")
            case Strategies.LLM_MUTATION:
                logger.info(f"[i] LLM mutation-based Fuzzer initialized")

    def _reload_feedback_data(self):
        try:
            with open(self.opts.get("feedback_log_file"), "r") as f:
                self.feedback_data = json.load(f)
        except:
            self.feedback_data = None

    def request(self, flow: http.HTTPFlow) -> None:
        if in_scope(self.scope, flow):
            logger.info(f"(->) Intercepted Request: {flow.request.method} {flow.request.path}")

    def response(self, flow: http.HTTPFlow) -> None:
        if in_scope(self.scope, flow):
            logger.info(f"(<-) Intercepted Response: {flow.response.status_code}")

            original_body = flow.response.text


            match self.strategy:
                case Strategies.BASELINE:
                    mutated_body = self.fuzzer.fuzz(original_body)
                    flow.response.text = mutated_body
                    logger.info(f"[Baseline] Mutated Response: {mutated_body[:100]}...")
                case Strategies.LLM_GENERATION:
                    self._reload_feedback_data()
                    logger.info(f"LLM Generation: {flow.response.text}")
                case Strategies.LLM_MUTATION:
                    self._reload_feedback_data()
                    logger.info(f"LLM Mutation: {flow.response.text}")



def init_proxy(scope: str, strategy: Strategies, fuzz_opts: dict|None = None):

    opts = options.Options(listen_host='0.0.0.0', listen_port=8080, ssl_insecure=True)
    master = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.addons.add(InterceptionAddon(scope=scope, strategy=strategy, opts=fuzz_opts))
    logger.info(f"Listening on {opts.listen_host}:{opts.listen_port}")
    return master