from mitmproxy import http
import enum


class Strategies(enum.Enum):
    BASELINE = 0
    LLM_GENERATION = 1
    LLM_MUTATION = 2


def in_scope(host: str, flow: http.HTTPFlow) -> bool:
    if len(host.split(":")) == 2:
        host, port = host.split(":")
        return flow.request.host == host and flow.request.port == int(port)
    return flow.request.host == host
