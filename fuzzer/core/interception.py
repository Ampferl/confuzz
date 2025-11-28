from mitmproxy import http, options
from mitmproxy.tools import dump

from utils import in_scope, Strategies
from core.baseline.fuzzer import BaselineFuzzer

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

# Disable logs from mitmproxy
logging.getLogger("mitmproxy").setLevel(logging.CRITICAL + 10)
logging.getLogger("mitmproxy").propagate = False


class InterceptionAddon:
    def __init__(self, scope: str, strategy: Strategies) -> None:
        self.scope = scope
        self.strategy = strategy
        self.fuzzer = None

        match strategy:
            case Strategies.BASELINE:
                self.fuzzer = BaselineFuzzer()
                logger.info(f"[i] Baseline Fuzzer initialized")
            case Strategies.LLM_GENERATION:
                logger.info(f"[i] LLM generation-based Fuzzer initialized")
            case Strategies.LLM_MUTATION:
                logger.info(f"[i] LLM mutation-based Fuzzer initialized")


    def request(self, flow: http.HTTPFlow) -> None:
        if in_scope(self.scope, flow):
            logger.info(f"(->) Intercepted Request: {flow.request.method} {flow.request.path}")

    def response(self, flow: http.HTTPFlow) -> None:
        if in_scope(self.scope, flow):
            logger.info(f"(<-) Intercepted Response: {flow.response.status_code}")
            match self.strategy:
                case Strategies.BASELINE:
                    logger.info(f"Baseline: {flow.response.text}")
                case Strategies.LLM_GENERATION:
                    logger.info(f"LLM Generation: {flow.response.text}")
                case Strategies.LLM_MUTATION:
                    logger.info(f"LLM Mutation: {flow.response.text}")



def init_proxy(scope: str, strategy: Strategies):

    opts = options.Options(listen_host='0.0.0.0', listen_port=8080, ssl_insecure=True)
    master = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.addons.add(InterceptionAddon(scope=scope, strategy=strategy))
    logger.info(f"Listening on {opts.listen_host}:{opts.listen_port}")
    return master