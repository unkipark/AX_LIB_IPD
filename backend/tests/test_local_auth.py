"""AUTH_MODE=local (기본값): 사번 + 비밀번호. SSO 왕복 없이 실제 세션 쿠키로 검증합니다."""
from __future__ import annotations

from app.auth_oidc import upsert_user
from app.config import settings
from app.models import User

SIGNUP = {"loginId": "E1001", "password": "secret-pass", "name": "홍길동", "department": "AX혁신팀"}
ART = {"title": "t", "summary": "s", "type": "skill", "tools": ["claude_code"]}


def signup(client, **over):
    return client.post("/api/auth/local/signup", json={**SIGNUP, **over})


def login(client, login_id="E1001", password="secret-pass"):
    return client.post("/api/auth/local/login", json={"loginId": login_id, "password": password})


def test_auth_config_lists_departments_for_signup(client):
    assert client.get("/api/auth/config").json() == {"mode": "local", "signup": True, "departments": []}
    signup(client)
    assert client.get("/api/auth/config").json()["departments"] == ["AX혁신팀"]


def test_signup_logs_in_and_sets_emp_no(client):
    r = signup(client)
    assert r.status_code == 201, r.text
    me = client.get("/api/me").json()
    assert (me["loginId"], me["empNo"], me["department"], me["role"]) == ("E1001", "E1001", "AX혁신팀", "user")
    assert client.post("/api/artifacts", json=ART).json()["department"] == "AX혁신팀"


def test_signup_validation_and_duplicates(client):
    assert signup(client, password="short").status_code == 422
    assert signup(client, loginId="한글사번").status_code == 422
    assert signup(client, name="   ").status_code == 422
    assert signup(client).status_code == 201
    assert signup(client).status_code == 409


def test_signup_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "local_signup", False)
    assert signup(client).status_code == 403


def test_login_logout_and_wrong_password(client):
    signup(client)
    client.get("/api/auth/logout", follow_redirects=False)
    assert client.get("/api/me").status_code == 401
    assert login(client, password="wrong-pass").status_code == 401
    assert login(client, login_id="nobody").status_code == 401
    assert login(client).status_code == 200
    assert client.get("/api/me").status_code == 200
    r = client.get("/api/auth/logout", follow_redirects=False)
    assert r.headers["location"] == "/login"


def test_lockout_after_repeated_failures(client, monkeypatch):
    monkeypatch.setattr(settings, "login_max_failures", 3)
    signup(client)
    for _ in range(3):
        assert login(client, password="wrong-pass").status_code == 401
    r = login(client)  # 맞는 비밀번호여도 잠금 중에는 거부
    assert r.status_code == 429 and "분 후" in r.json()["detail"]


def test_admin_ids_grants_admin_on_login(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_ids", "E1001")
    signup(client)
    assert client.get("/api/me").json()["role"] == "admin"


def test_profile_and_password_change(client):
    signup(client)
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    r = client.put("/api/me", json={"name": "홍길동", "department": "설계팀", "email": ""})
    assert r.json()["department"] == "설계팀" and r.json()["email"] is None
    # 이미 등록한 산출물의 부서는 등록 당시 값을 유지합니다.
    assert client.get(f"/api/artifacts/{aid}").json()["department"] == "AX혁신팀"

    bad = client.put("/api/me/password", json={"currentPassword": "nope", "newPassword": "new-secret-1"})
    assert bad.status_code == 400
    ok = client.put("/api/me/password", json={"currentPassword": "secret-pass", "newPassword": "new-secret-1"})
    assert ok.status_code == 204
    client.get("/api/auth/logout", follow_redirects=False)
    assert login(client).status_code == 401
    assert login(client, password="new-secret-1").status_code == 200


def test_admin_user_management(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_ids", "A0001")
    signup(client)  # 일반 사용자 E1001
    assert client.get("/api/admin/users").status_code == 403
    client.get("/api/auth/logout", follow_redirects=False)

    signup(client, loginId="A0001", name="관리자")
    users = {u["loginId"]: u for u in client.get("/api/admin/users").json()}
    target = users["E1001"]["id"]
    me_id = users["A0001"]["id"]

    assert client.put(f"/api/admin/users/{me_id}", json={"role": "user"}).status_code == 400
    temp = client.post(f"/api/admin/users/{target}/reset-password").json()["tempPassword"]
    assert client.put(f"/api/admin/users/{target}", json={"isActive": False}).json()["isActive"] is False
    created = client.post("/api/admin/users", json={**SIGNUP, "loginId": "E2002", "name": "이영희"})
    assert created.status_code == 201

    client.get("/api/auth/logout", follow_redirects=False)
    assert login(client, password=temp).status_code == 403  # 비활성 계정
    assert login(client, login_id="E2002").status_code == 200


def test_deactivated_user_loses_existing_session(client, db):
    signup(client)
    user = db.query(User).filter_by(login_id="E1001").one()
    user.is_active = False
    db.commit()
    assert client.get("/api/me").status_code == 401


def test_switching_to_sso_links_existing_local_account(client, db):
    """local 로 쓰던 사번 E1001 계정에 SSO 로그인이 연결되어 산출물이 그대로 남아야 합니다."""
    signup(client)
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    local_id = client.get("/api/me").json()["id"]

    user = upsert_user(db, {"sub": "sso-xyz", "employee_number": "E1001", "name": "홍길동", "department": "AX팀"})
    db.commit()
    assert user.id == local_id and user.external_id == "sso-xyz" and user.department == "AX팀"
    assert client.get(f"/api/artifacts/{aid}").json()["owner"]["id"] == local_id
