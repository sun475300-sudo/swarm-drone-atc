"""P712: JWT-HMAC RBAC 단위 테스트."""

from __future__ import annotations

import time

import pytest


class TestJWTIssueAndVerify:
    def test_roundtrip(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="test-secret-32-chars-long-enough!!")
        token = auth.issue("user1", Role.OPERATOR)
        payload = auth.verify(token)
        assert payload.sub == "user1"
        assert payload.role == Role.OPERATOR

    def test_tampered_signature_rejected(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="test-secret!!")
        token = auth.issue("user1", Role.VIEWER)
        parts = token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        with pytest.raises(ValueError, match="서명"):
            auth.verify(".".join(parts))

    def test_expired_token_rejected(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="s3cr3t", ttl_sec=1)
        token = auth.issue("user1", Role.VIEWER)
        # 만료 직후 재발행 없이 verify
        import time as _time
        _time.sleep(1.1)
        with pytest.raises(ValueError, match="만료"):
            auth.verify(token)

    def test_malformed_token_rejected(self):
        from api.auth import JWTAuth
        auth = JWTAuth()
        with pytest.raises(ValueError):
            auth.verify("notavalidtoken")

    def test_alg_confusion_rejected(self):
        """alg: 'none' 혼동 공격 방지 테스트."""
        import base64, json
        from api.auth import JWTAuth
        auth = JWTAuth(secret_key="test-secret")
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "attacker", "role": "ADMIN",
                        "iat": time.time(), "exp": time.time() + 3600, "jti": "x"}).encode()
        ).rstrip(b"=").decode()
        evil_token = f"{header}.{payload}."
        with pytest.raises(ValueError, match="알고리즘"):
            auth.verify(evil_token)


class TestRBACRoles:
    def test_require_role_viewer_ok(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="secret!!")
        token = auth.issue("u1", Role.OPERATOR)
        payload = auth.require_role(token, Role.VIEWER)
        assert payload.sub == "u1"

    def test_require_role_admin_denied_for_operator(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="secret!!")
        token = auth.issue("u1", Role.OPERATOR)
        with pytest.raises(PermissionError, match="권한"):
            auth.require_role(token, Role.ADMIN)

    def test_role_hierarchy_viewer_lt_admin(self):
        from api.auth import Role
        assert Role.VIEWER < Role.ADMIN
        assert Role.ADMIN >= Role.OPERATOR

    def test_admin_passes_all_levels(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="sec!!")
        token = auth.issue("admin_user", Role.ADMIN)
        for role in Role:
            payload = auth.require_role(token, role)
            assert payload.role == Role.ADMIN


class TestAuditLog:
    def test_audit_records_on_issue(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="s3cr3t!")
        auth.issue("u1", Role.VIEWER)
        assert len(auth.audit) >= 1

    def test_audit_records_access_denied(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="s3cr3t!")
        token = auth.issue("u1", Role.VIEWER)
        try:
            auth.require_role(token, Role.ADMIN)
        except PermissionError:
            pass
        recent = auth.audit.recent(10)
        actions = [e.action for e in recent]
        assert "access_denied" in actions

    def test_revoke_invalidates_token(self):
        from api.auth import JWTAuth, Role
        auth = JWTAuth(secret_key="s3cr3t!")
        token = auth.issue("u1", Role.OPERATOR)
        auth.revoke(token)
        with pytest.raises(ValueError, match="폐기"):
            auth.verify(token)


class TestGetAuth:
    def test_get_auth_singleton(self):
        import os
        import api.auth as auth_mod
        os.environ["SDACS_JWT_SECRET"] = "test-singleton-secret-long-enough!"
        auth_mod._default_auth = None   # 싱글톤 초기화
        a1 = auth_mod.get_auth()
        a2 = auth_mod.get_auth()
        assert a1 is a2

    def test_get_auth_raises_without_secret(self):
        import os
        import api.auth as auth_mod
        os.environ.pop("SDACS_JWT_SECRET", None)
        auth_mod._default_auth = None
        with pytest.raises(RuntimeError, match="SDACS_JWT_SECRET"):
            auth_mod.get_auth()
        # 복구
        os.environ["SDACS_JWT_SECRET"] = "restored-secret-long-enough!!"
        auth_mod._default_auth = None
