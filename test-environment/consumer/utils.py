from datetime import datetime
from urllib.parse import urlparse
import logging
import sqlite3
import httpx
import json
import os

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://producer:5000/")
PROXY_URL = os.getenv("HTTP_PROXY")

logger = logging.getLogger("consumer")

eval_logger = logging.getLogger("evaluation")
eval_logger.setLevel(logging.INFO)

if not eval_logger.handlers:
    handler = logging.FileHandler("consumer_eval.log")
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    eval_logger.addHandler(handler)

def log_eval(scenario: int, payload: str, details: str, status_code: int = 200, exploited: bool = False):
    entry = {
        "scenario": scenario,
        "timestamp": datetime.now().isoformat(),
        "payload_received": payload,
        "details": details,
        "status_code": status_code,
        "exploited": exploited
    }
    eval_logger.info(json.dumps(entry))


async def fetch_data_from_producer(url):
    mounts = {}
    if PROXY_URL:
        mounts = {"http://": httpx.AsyncHTTPTransport(proxy=PROXY_URL)}

    async with httpx.AsyncClient(mounts=mounts, verify=False, timeout=None) as client:
        try:
            resp = await client.get(f"{PRODUCER_URL}{url}")
            return resp
        except Exception as e:
            logger.error(f"Error fetching data from producer: {e}")
            return  None


def init_log_file():
    with open("app.log", "w") as f:
        f.write("[+] Log file initialized")


def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS orders')
    c.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT, category TEXT)')
    c.execute("INSERT INTO orders (item, category) VALUES ('Laptop', 'electronics')")
    c.execute("INSERT INTO orders (item, category) VALUES ('Cable', 'accessories')")
    c.execute("INSERT INTO orders (item, category) VALUES ('Phone', 'electronics')")
    conn.commit()
    conn.close()


def is_url(url):
  try:
    result = urlparse(url)
    return all([result.scheme, result.netloc])
  except ValueError:
    return False
