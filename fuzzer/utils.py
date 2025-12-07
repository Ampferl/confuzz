from typing import List, Dict, Any, Optional
from core.strategies import Strategies
from mitmproxy import http
import difflib
import logging
import json

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'


eval_logger = logging.getLogger("fuzzer-evaluation")
eval_logger.setLevel(logging.INFO)

def init_logger(strategy: Strategies):
    if not eval_logger.handlers:
        handler = logging.FileHandler("fuzzer_eval.log")
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        eval_logger.addHandler(handler)
        eval_logger.info(f"Evaluation logger initialized for {strategy.name}")

def log_eval(feedback):
    eval_logger.info(json.dumps(feedback))


def colorize_changes(original: str, modified: str, mode: str = "diff"):
    matcher = difflib.SequenceMatcher(None, original, modified)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            result.append(original[i1:i2])
        elif mode == "diff":
            if tag == 'delete':
                result.append(f"{RED}{original[i1:i2]}{RESET}")
            elif tag == 'insert':
                result.append(f"{GREEN}{modified[j1:j2]}{RESET}")
            elif tag == 'replace':
                result.append(f"{RED}{original[i1:i2]}{RESET}{GREEN}{modified[j1:j2]}{RESET}")
        elif mode == "changes":
            if tag == 'delete':
                pass
            elif tag == 'insert':
                result.append(f"{YELLOW}{modified[j1:j2]}{RESET}")
            elif tag == 'replace':
                result.append(f"{YELLOW}{modified[j1:j2]}{RESET}")
    return "".join(result)


def in_scope(host: str, flow: http.HTTPFlow) -> bool:
    if len(host.split(":")) == 2:
        host, port = host.split(":")
        return flow.request.host == host and flow.request.port == int(port)
    return flow.request.host == host



def filter_last_elements(items: Optional[list], search: str, key: str, amount: int) -> List[Dict[str, Any]]:

    if not items:
        return []
    if amount <= 0:
        return []

    matches: List[Dict[str, Any]] = []
    for d in reversed(items):
        if not isinstance(d, dict):
            continue
        if d.get(key) == search:
            matches.append(d)
            if len(matches) == amount:
                break
    return list(reversed(matches))
