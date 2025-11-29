from mitmproxy import http



def in_scope(host: str, flow: http.HTTPFlow) -> bool:
    if len(host.split(":")) == 2:
        host, port = host.split(":")
        return flow.request.host == host and flow.request.port == int(port)
    return flow.request.host == host
