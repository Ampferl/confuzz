import logging
import sqlite3
import httpx
import os

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://producer:5000/")
PROXY_URL = os.getenv("HTTP_PROXY")

logger = logging.getLogger("consumer")


async def fetch_data_from_producer(url):
    mounts = {}
    if PROXY_URL:
        mounts = {"http://": httpx.AsyncHTTPTransport(proxy=PROXY_URL)}

    async with httpx.AsyncClient(mounts=mounts, verify=False, timeout=None) as client:
        try:
            resp = await client.get(f"{PRODUCER_URL}{url}")
            return resp
        except Exception as e:
            logger.error(f"PROXY_URL: {PROXY_URL}")
            logger.error(f"Error fetching data from producer: {e}")
            return  None


def init_log_file():
    with open("app.log", "w") as f:
        f.write("[+] Log file initialized")