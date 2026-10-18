"""Shared HTTP session: identifies us politely and retries temporary failures."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "GLP1-Launch-Intelligence research project (github.com/Swagata-Bhowmik/GLP1-Launch-Intelligence)"


def session() -> requests.Session:
    """A requests.Session with retries and exponential backoff.

    Retries on rate limits (429) and server errors (5xx): wait 1s, 2s, 4s, ... before trying again.
    """
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=6, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "HEAD"], respect_retry_after_header=True)
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s
