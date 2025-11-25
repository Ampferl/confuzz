# Test Environment Endpoints
This documentation contains the `curl` commands to request all scenario endpoints of the test environment, including a description of what happens in each scenario.

## Scenario 0
```shell
curl http://localhost:5050/api/v1/admin/view-logs
```

## Scenario 1
```shell
curl -X POST http://localhost:5050/api/v1/users/sync/1
```

## Scenario 2
```shell
curl -X POST http://localhost:5050/api/v1/auth/init
```

## Scenario 3
```shell
curl http://localhost:5050/api/v1/profile/avatar
```

## Scenario 4
```shell
curl http://localhost:5050/api/v1/shop/inventory
```

## Scenario 5
```shell
curl http://localhost:5050/api/v1/orders/recommendations
```
