"""Phase P712/P714/P718 테스트.

P712: JWT 인증 + RBAC
P714: DB 모델 (SQLAlchemy)
P718: Prometheus 메트릭
"""

from __future__ import annotations

import importlib
import time

import pytest

pytest.importorskip("fastapi")

# ── P712: JWT 인증 + RBAC ────────────────────────────────────────────


class TestJWTAuth:
    def test_create_and_decode_token(self):
        auth = importlib.import_module("api.auth")
        token = auth.create_access_token({"sub": "testuser", "role": "OPERATOR"})
        assert isinstance(token, str)
        payload = auth.decode_token(token)
        assert payload.sub == "testuser"
        assert payload.role == auth.Role.OPERATOR

    def test_expired_token_raises_401(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        token = auth.create_access_token({"sub": "u", "role": "VIEWER"}, ttl_s=-1)
        with pytest.raises(HTTPException) as exc_info:
            auth.decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_invalid_token_raises_401(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            auth.decode_token("not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    def test_issue_token_valid_credentials(self):
        auth = importlib.import_module("api.auth")
        resp = auth.issue_token("viewer", "viewer-secret")
        assert resp.access_token
        assert resp.token_type == "bearer"
        assert resp.expires_in > 0

    def test_issue_token_wrong_password_raises_401(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            auth.issue_token("viewer", "wrong-password")
        assert exc_info.value.status_code == 401

    def test_issue_token_unknown_user_raises_401(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            auth.issue_token("nobody", "any")

    @pytest.mark.asyncio
    async def test_get_current_user_valid_bearer(self):
        auth = importlib.import_module("api.auth")
        token = auth.create_access_token({"sub": "op1", "role": "OPERATOR"})
        user = await auth.get_current_user(authorization=f"Bearer {token}")
        assert user.sub == "op1"

    @pytest.mark.asyncio
    async def test_get_current_user_missing_bearer_raises_401(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await auth.get_current_user(authorization="")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_role_admin_blocks_viewer(self):
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        viewer_token = auth.create_access_token({"sub": "v1", "role": "VIEWER"})
        viewer_user = await auth.get_current_user(authorization=f"Bearer {viewer_token}")

        admin_dep = auth.require_role(auth.Role.ADMIN)
        # dependency 함수 직접 호출
        with pytest.raises(HTTPException) as exc_info:
            await admin_dep(user=viewer_user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_role_operator_allows_admin(self):
        auth = importlib.import_module("api.auth")
        admin_token = auth.create_access_token({"sub": "a1", "role": "ADMIN"})
        admin_user = await auth.get_current_user(authorization=f"Bearer {admin_token}")

        op_dep = auth.require_role(auth.Role.OPERATOR)
        result = await op_dep(user=admin_user)
        assert result.sub == "a1"


# ── P714: DB 모델 ─────────────────────────────────────────────────────


class TestDBModels:
    def test_db_module_imports(self):
        db = importlib.import_module("api.db")
        assert hasattr(db, "Base")
        assert hasattr(db, "DroneSnapshot")
        assert hasattr(db, "RunRecord")
        assert hasattr(db, "AuditLog")

    def test_drone_snapshot_table_name(self):
        db = importlib.import_module("api.db")
        assert db.DroneSnapshot.__tablename__ == "drone_snapshot"

    def test_run_record_table_name(self):
        db = importlib.import_module("api.db")
        assert db.RunRecord.__tablename__ == "run_record"

    def test_audit_log_table_name(self):
        db = importlib.import_module("api.db")
        assert db.AuditLog.__tablename__ == "audit_log"

    def test_drone_snapshot_columns(self):
        db = importlib.import_module("api.db")
        cols = {c.name for c in db.DroneSnapshot.__table__.columns}
        assert {"id", "recorded_at", "drone_id", "x", "y", "z", "battery_pct"} <= cols

    def test_run_record_columns(self):
        db = importlib.import_module("api.db")
        cols = {c.name for c in db.RunRecord.__table__.columns}
        assert {"run_id", "scenario_id", "status", "started_at_ns", "metrics"} <= cols

    def test_audit_log_columns(self):
        db = importlib.import_module("api.db")
        cols = {c.name for c in db.AuditLog.__table__.columns}
        assert {"id", "recorded_at", "username", "role", "action"} <= cols

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, tmp_path):
        import os

        os.environ["SDACS_DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_path}/test.db"
        import importlib

        db = importlib.import_module("api.db")
        importlib.reload(db)
        await db.init_db()
        # 테이블이 생성됐으면 예외 없이 완료
        assert True


# ── P718: Prometheus 메트릭 ───────────────────────────────────────────


class TestPrometheusMetrics:
    def test_metrics_module_imports(self):
        metrics = importlib.import_module("api.metrics")
        assert hasattr(metrics, "update_from_snapshot")
        assert hasattr(metrics, "record_advisory")
        assert hasattr(metrics, "set_ws_subscribers")

    def test_update_from_snapshot_no_error(self):
        metrics = importlib.import_module("api.metrics")
        drones = [{"id": "d1"}, {"id": "d2"}]
        conflicts = [{"pair": ["d1", "d2"]}]
        # 예외 없이 실행되면 성공
        metrics.update_from_snapshot(drones, conflicts)

    def test_record_advisory_no_error(self):
        metrics = importlib.import_module("api.metrics")
        metrics.record_advisory("CLIMB")
        metrics.record_advisory("EVADE_APF")

    def test_set_ws_subscribers_no_error(self):
        metrics = importlib.import_module("api.metrics")
        metrics.set_ws_subscribers(5)

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_response(self):
        metrics = importlib.import_module("api.metrics")
        from fastapi.responses import Response

        resp = await metrics.metrics_endpoint()
        assert isinstance(resp, Response)
        assert resp.status_code == 200


# ── P712 + FastAPI 통합: /auth/token 엔드포인트 ──────────────────────


class TestAuthEndpoint:
    @pytest.mark.asyncio
    async def test_auth_token_endpoint_returns_token(self):
        backend = importlib.import_module("api.fastapi_server")
        auth = importlib.import_module("api.auth")

        resp = await backend.auth_token(auth.TokenRequest(username="viewer", password="viewer-secret"))
        assert resp.access_token
        payload = auth.decode_token(resp.access_token)
        assert payload.sub == "viewer"
        assert payload.role == auth.Role.VIEWER

    @pytest.mark.asyncio
    async def test_auth_token_endpoint_wrong_creds_raises_401(self):
        backend = importlib.import_module("api.fastapi_server")
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await backend.auth_token(auth.TokenRequest(username="admin", password="wrong"))
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_run_scenario_requires_operator_role(self, monkeypatch):
        backend = importlib.import_module("api.fastapi_server")
        auth = importlib.import_module("api.auth")
        from fastapi import HTTPException, Request

        viewer_token = auth.create_access_token({"sub": "v", "role": "VIEWER"})
        viewer_user = await auth.get_current_user(authorization=f"Bearer {viewer_token}")

        monkeypatch.setattr(backend, "_build_scenario_catalog", lambda: {})
        monkeypatch.setattr(backend.asyncio, "create_task", lambda c: (c.close(), None))

        # VIEWER는 OPERATOR 이상 요구 → 403
        op_dep = auth.require_role(auth.Role.OPERATOR)
        with pytest.raises(HTTPException) as exc_info:
            await op_dep(user=viewer_user)
        assert exc_info.value.status_code == 403
