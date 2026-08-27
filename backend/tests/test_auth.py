from datetime import timedelta

from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User, UserSession
from app.models.user import AuditEvent
from app.security import hash_password, utcnow, verify_password
from app.scripts.create_admin import _create_first_admin


def test_password_hash_and_generic_login_error(client, db):
    user = db.scalar(select(User).where(User.email == "test-admin@example.com"))
    assert user.password_hash != "test-password-123"
    assert verify_password("test-password-123", user.password_hash)
    unknown = client.post("/api/auth/login", json={"email":"missing@example.com","password":"incorrect-password"})
    incorrect = client.post("/api/auth/login", json={"email":"test-admin@example.com","password":"incorrect-password"})
    assert unknown.status_code == incorrect.status_code == 401
    assert unknown.json() == incorrect.json() == {"detail":"Invalid email or password"}


def test_login_cookie_me_logout_and_revocation(client, db):
    response = client.post("/api/auth/login", json={"email":"TEST-ADMIN@example.com","password":"test-password-123"})
    assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"] and "SameSite=lax" in response.headers["set-cookie"]
    assert "password_hash" not in response.json()
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_user_management_must_change_and_final_admin(client, db):
    created = client.post("/api/users", json={"email":"Cashier@Example.com","display_name":"Cashier","role":"CASHIER","temporary_password":"temporary-123"})
    assert created.status_code == 201 and created.json()["must_change_password"] is True
    duplicate = client.post("/api/users", json={"email":"cashier@example.com","display_name":"Other","role":"CASHIER","temporary_password":"temporary-123"})
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail":"A user with this email already exists"}
    assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.action == "USER_CREATED")))) == 1
    admin_id = db.scalar(select(User).where(User.role == "ADMIN")).id
    assert client.patch(f"/api/users/{admin_id}", json={"is_active":False}).status_code == 409
    assert client.patch(f"/api/users/{admin_id}", json={"role":"MANAGER"}).status_code == 409
    for field in ("email", "display_name", "role", "is_active"):
        assert client.patch(f"/api/users/{created.json()['id']}", json={field: None}).status_code == 422
    assert client.patch(f"/api/users/{created.json()['id']}", json={"display_name":"   "}).status_code == 422
    assert client.post("/api/users", json={"email":"blank@example.com","display_name":"   ","role":"CASHIER","temporary_password":"temporary-123"}).status_code == 422


def test_expired_and_inactive_sessions_are_rejected(client, db):
    session = db.scalar(select(UserSession).where(UserSession.revoked_at.is_(None)))
    session.expires_at = utcnow() - timedelta(seconds=1); db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_bootstrap_with_no_users(db):
    user = _create_first_admin(db, "First@Example.com", "First Admin", "bootstrap-password", "bootstrap-password")
    assert user.email == "first@example.com" and user.is_active and verify_password("bootstrap-password", user.password_hash)


def test_bootstrap_upgrades_inactive_passwordless_legacy_admin(db):
    legacy = User(email="legacy@example.com", display_name="Legacy", password_hash=None, role="ADMIN", is_active=False, must_change_password=True)
    db.add(legacy); db.commit()
    result = _create_first_admin(db, "LEGACY@example.com", "Recovered Admin", "bootstrap-password", "bootstrap-password")
    assert result.id == legacy.id and result.is_active and result.display_name == "Recovered Admin"
    assert verify_password("bootstrap-password", result.password_hash)


def test_bootstrap_refuses_active_usable_admin(db):
    db.add(User(email="admin@example.com", display_name="Admin", password_hash=hash_password("existing-password"), role="ADMIN", is_active=True, must_change_password=False)); db.commit()
    try:
        _create_first_admin(db, "new@example.com", "New", "bootstrap-password", "bootstrap-password")
    except ValueError as error:
        assert "active administrator" in str(error)
    else:
        raise AssertionError("bootstrap unexpectedly succeeded")


def test_bootstrap_refuses_duplicate_nonlegacy_email(db):
    db.add(User(email="used@example.com", display_name="Cashier", password_hash=hash_password("existing-password"), role="CASHIER", is_active=False, must_change_password=False)); db.commit()
    try:
        _create_first_admin(db, "USED@example.com", "New", "bootstrap-password", "bootstrap-password")
    except ValueError as error:
        assert "already in use" in str(error)
    else:
        raise AssertionError("bootstrap unexpectedly succeeded")


def test_change_password_revokes_other_sessions(unauthenticated_client, db):
    user = User(email="change@example.com", display_name="Change", password_hash=hash_password("original-password"), role="CASHIER", is_active=True, must_change_password=False)
    db.add(user); db.commit()
    first = unauthenticated_client
    assert first.post("/api/auth/login", json={"email":user.email,"password":"original-password"}).status_code == 200
    # Creating a second session directly represents another authenticated browser.
    from app.models.user import UserSession
    from app.security import token_digest
    second = UserSession(user_id=user.id, token_hash=token_digest("other-session"), expires_at=utcnow()+timedelta(hours=1))
    db.add(second); db.commit()
    assert first.post("/api/auth/change-password", json={"current_password":"original-password","new_password":"replacement-password"}).status_code == 200
    db.refresh(second); assert second.revoked_at is not None
    assert first.post("/api/auth/login", json={"email":user.email,"password":"original-password"}).status_code == 401
    assert first.post("/api/auth/login", json={"email":user.email,"password":"replacement-password"}).status_code == 200


def test_inactive_user_and_must_change_restriction(unauthenticated_client, db):
    inactive = User(email="inactive@example.com", display_name="Inactive", password_hash=hash_password("inactive-password"), role="CASHIER", is_active=False, must_change_password=False)
    forced = User(email="forced@example.com", display_name="Forced", password_hash=hash_password("temporary-password"), role="CASHIER", is_active=True, must_change_password=True)
    db.add_all([inactive, forced]); db.commit()
    assert unauthenticated_client.post("/api/auth/login", json={"email":inactive.email,"password":"inactive-password"}).status_code == 401
    assert unauthenticated_client.post("/api/auth/login", json={"email":forced.email,"password":"temporary-password"}).status_code == 200
    assert unauthenticated_client.get("/api/products").status_code == 403
    assert unauthenticated_client.get("/api/auth/me").status_code == 200
    assert unauthenticated_client.post("/api/auth/change-password", json={"current_password":"temporary-password","new_password":"permanent-password"}).status_code == 200


def test_deactivation_permanently_revokes_old_session(client, db):
    created = client.post("/api/users", json={"email":"revoked@example.com","display_name":"Revoked User","role":"CASHIER","temporary_password":"temporary-123"}).json()
    with TestClient(app) as cashier_browser:
        assert cashier_browser.post("/api/auth/login", json={"email":"revoked@example.com","password":"temporary-123"}).status_code == 200
        assert client.patch(f"/api/users/{created['id']}", json={"is_active":False}).status_code == 200
        assert cashier_browser.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me").status_code == 200
        assert client.patch(f"/api/users/{created['id']}", json={"is_active":True}).status_code == 200
        assert cashier_browser.get("/api/auth/me").status_code == 401
        assert cashier_browser.post("/api/auth/login", json={"email":"revoked@example.com","password":"temporary-123"}).status_code == 200
        assert cashier_browser.get("/api/auth/me").status_code == 200
