"""TASK-012 測試：Lambda handler（Mangum）可正確處理模擬的 API Gateway event。"""
from fastapi.testclient import TestClient

from app import app
from auth import get_current_user
from lambda_handler import handler


def _api_gateway_v2_event(path: str, method: str = "GET"):
    """建構最小可用的 API Gateway HTTP API v2 event。"""
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-agent",
            },
            "requestId": "test-request-id",
            "routeKey": f"{method} {path}",
            "stage": "$default",
            "time": "13/Jul/2026:00:00:00 +0000",
            "timeEpoch": 1752364800,
        },
        "isBase64Encoded": False,
    }


class _FakeLambdaContext:
    function_name = "aimom-api"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:ap-northeast-1:123456789012:function:aimom-api"
    aws_request_id = "test-request-id"


def test_lambda_handler_health_check_returns_200():
    event = _api_gateway_v2_event("/api/health")
    response = handler(event, _FakeLambdaContext())

    assert response["statusCode"] == 200
    assert "ok" in response["body"]


def test_lambda_handler_unknown_route_returns_404():
    event = _api_gateway_v2_event("/api/does-not-exist")
    response = handler(event, _FakeLambdaContext())

    assert response["statusCode"] == 404


def test_health_check_v2_returns_ok_and_version_without_auth():
    """SDLCAIP2-2：未帶任何認證 token 呼叫 /api/health-check-v2 應成功。"""
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)

    response = client.get("/api/health-check-v2")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_health_check_v2_route_has_no_auth_dependency():
    """SDLCAIP2-2：/api/health-check-v2 路由不應依賴 Depends(get_current_user)。"""
    route = next(r for r in app.routes if getattr(r, "path", None) == "/api/health-check-v2")

    dependency_calls = {dep.call for dep in route.dependant.dependencies}
    assert get_current_user not in dependency_calls
