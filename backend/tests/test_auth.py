from datetime import timedelta

from sqlalchemy import select

from app.models.user import User, UserSession
from app.security import hash_password, utcnow, verify_password


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
    admin_id = db.scalar(select(User).where(User.role == "ADMIN")).id
    assert client.patch(f"/api/users/{admin_id}", json={"is_active":False}).status_code == 409


def test_expired_and_inactive_sessions_are_rejected(client, db):
    session = db.scalar(select(UserSession).where(UserSession.revoked_at.is_(None)))
    session.expires_at = utcnow() - timedelta(seconds=1); db.commit()
    assert client.get("/api/auth/me").status_code == 401
