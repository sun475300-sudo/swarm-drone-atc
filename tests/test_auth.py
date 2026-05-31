"""P712 JWT/RBAC 단위 테스트."""
import logging
import pytest
from src.auth.jwt_handler import create_access_token, decode_token, TokenData
from src.auth.rbac import Role, Permission, ROLE_PERMISSIONS, require_permission
from src.auth.audit_log import log_auth_event


class TestJWTHandler:
    def test_create_and_decode_token(self):
        token = create_access_token("user1", role="operator")
        data = decode_token(token)
        assert data.sub == "user1"
        assert data.role == "operator"
        assert isinstance(data, TokenData)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            decode_token("not.a.valid.token")

    def test_tampered_signature_raises(self):
        token = create_access_token("user1")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.INVALIDSIG"
        with pytest.raises(ValueError):
            decode_token(tampered)

    def test_default_role_is_viewer(self):
        token = create_access_token("user2")
        data = decode_token(token)
        assert data.role == "viewer"

    def test_token_has_exp(self):
        token = create_access_token("user3")
        data = decode_token(token)
        assert data.exp is not None
        assert data.exp > 0


class TestRBAC:
    def test_admin_has_all_permissions(self):
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        for p in Permission:
            assert p in admin_perms

    def test_viewer_cannot_write_drone(self):
        assert Permission.DRONE_WRITE not in ROLE_PERMISSIONS[Role.VIEWER]

    def test_viewer_can_read(self):
        assert Permission.DRONE_READ in ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.AIRSPACE_READ in ROLE_PERMISSIONS[Role.VIEWER]

    def test_operator_can_command_drone(self):
        assert Permission.DRONE_CMD in ROLE_PERMISSIONS[Role.OPERATOR]

    def test_analyst_cannot_command(self):
        assert Permission.DRONE_CMD not in ROLE_PERMISSIONS[Role.ANALYST]

    def test_require_permission_admin(self):
        checker = require_permission(Permission.DRONE_WRITE)
        assert checker("admin") is True

    def test_require_permission_viewer_blocked(self):
        checker = require_permission(Permission.DRONE_WRITE)
        assert checker("viewer") is False

    def test_require_permission_unknown_role(self):
        checker = require_permission(Permission.DRONE_READ)
        assert checker("unknown_role") is False


class TestAuditLog:
    def test_success_event_logged_as_info(self, caplog):
        with caplog.at_level(logging.INFO, logger="sdacs.audit"):
            log_auth_event("login", "user1", resource="/api/drones", success=True)
        assert any("login" in r.message for r in caplog.records)

    def test_failure_event_logged_as_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="sdacs.audit"):
            log_auth_event("access_denied", "user2", resource="/api/admin", success=False)
        assert any("access_denied" in r.message for r in caplog.records)

    def test_log_event_contains_user(self, caplog):
        with caplog.at_level(logging.INFO, logger="sdacs.audit"):
            log_auth_event("token_issued", "alice")
        assert any("alice" in r.message for r in caplog.records)

    def test_log_event_optional_fields(self):
        # 예외 없이 실행되는지 확인
        log_auth_event("logout", "bob")
        log_auth_event("logout", "carol", resource=None, success=True, detail=None)
