import httpx

DEFAULT_TIMEOUT = httpx.Timeout(8.0, connect=4.0)
USER_AGENT = "solo-travel-planner/0.1"
