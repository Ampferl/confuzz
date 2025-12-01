CONSUMER_HOST = "http://localhost:5050"

SCENARIOS = {
    0: {"url": "/api/v1/admin/view-logs", "method": "GET", "expected_result": "root:x:0:0"},
    1: {"url": "/api/v1/users/sync/1", "method": "POST", "expected_result": "\"role\":\"admin\""},
    2: {"url": "/api/v1/auth/init", "method": "POST", "expected_result": "TIMEOUT"},
    3: {"url": "/api/v1/profile/avatar", "method": "GET", "expected_result": ""},
    4: {"url": "/api/v1/shop/inventory", "method": "GET", "expected_result": "Traceback"},
    5: {"url": "/api/v1/orders/recommendations", "method": "GET", "expected_result": "recommended_items"},
}