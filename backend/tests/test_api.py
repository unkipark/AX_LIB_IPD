from __future__ import annotations

from app.auth_oidc import upsert_user
from app.config import settings

ART = {
    "title": "PR 리뷰 자동화 skill",
    "summary": "Claude Code 로 PR 리뷰 초안을 만듭니다",
    "type": "skill",
    "status": "pilot",
    "process": "코드 리뷰",
    "timeSavedMin": 30,
    "tools": ["claude_code"],
    "tags": ["#리뷰", "리뷰", " 자동화 "],
}


def test_requires_login(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/artifacts").status_code == 401


def test_upsert_user_maps_claims_and_updates_on_relogin(db, monkeypatch):
    monkeypatch.setattr(settings, "oidc_claim_department", "org.dept")
    monkeypatch.setattr(settings, "admin_ids", "E100")
    u = upsert_user(db, {"sub": "abc", "name": "김철수", "employee_number": "E100", "org": {"dept": "설계팀"}})
    assert (u.name, u.department, u.emp_no) == ("김철수", "설계팀", "E100")
    assert settings.admin_id_set & {u.emp_no}
    u2 = upsert_user(db, {"sub": "abc", "name": "김철수", "employee_number": "E100", "org": {"dept": "AX팀"}})
    assert u2.id == u.id and u2.department == "AX팀"


def test_create_list_detail(client, login):
    login()
    r = client.post("/api/artifacts", json=ART)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tags"] == ["리뷰", "자동화"]
    assert body["department"] == "AX팀" and body["canEdit"] is True

    page = client.get("/api/artifacts", params={"q": "자동화"}).json()
    assert page["total"] == 1 and page["items"][0]["owner"]["name"] == "홍길동"
    assert client.get("/api/artifacts", params={"tool": "opencode"}).json()["total"] == 0
    assert client.get("/api/artifacts", params={"sort": "popular"}).json()["total"] == 1


def test_validation_rejects_unknown_type(client, login):
    login()
    assert client.post("/api/artifacts", json={**ART, "type": "nope"}).status_code == 422


def test_only_owner_or_admin_can_edit(client, login, db):
    login("u1")
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    login("u2", "이영희")
    assert client.put(f"/api/artifacts/{aid}", json=ART).status_code == 403
    assert client.get(f"/api/artifacts/{aid}").json()["canEdit"] is False
    admin = login("u3", "관리자")
    admin.role = "admin"
    assert client.put(f"/api/artifacts/{aid}", json={**ART, "status": "deployed"}).json()["status"] == "deployed"


def test_used_once_per_day_and_dashboard(client, login):
    login("u1")
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    login("u2", "이영희", "설계팀")
    assert client.post(f"/api/artifacts/{aid}/used").json() == {"useCount": 1}
    assert client.post(f"/api/artifacts/{aid}/used").json() == {"useCount": 1}
    assert client.get(f"/api/artifacts/{aid}").json()["usedByMeToday"] is True

    d = client.get("/api/dashboard").json()
    assert d["kpi"]["artifacts"] == 1 and d["kpi"]["uses"] == 1 and d["kpi"]["savedHours"] == 0.5
    assert {s["key"]: s["count"] for s in d["byStatus"]}["pilot"] == 1
    assert d["topUsed"][0]["id"] == aid and d["topContributors"][0]["name"] == "홍길동"
    assert d["monthly"][-1]["created"] == 1 and len(d["monthly"]) == 12


def test_file_upload_download_delete(client, login, monkeypatch):
    login()
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    r = client.post(f"/api/artifacts/{aid}/files", files={"file": ("가이드.md", b"# hello", "text/markdown")})
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    dl = client.get(f"/api/files/{fid}")
    assert dl.content == b"# hello" and "filename*=utf-8''" in dl.headers["content-disposition"]
    assert client.get(f"/api/artifacts/{aid}").json()["downloadCount"] == 1

    monkeypatch.setattr(settings, "max_upload_mb", 0)
    assert client.post(f"/api/artifacts/{aid}/files", files={"file": ("big.bin", b"x")}).status_code == 413

    assert client.delete(f"/api/files/{fid}").status_code == 204
    assert client.delete(f"/api/artifacts/{aid}").status_code == 204
    assert not (settings.upload_dir / str(aid)).exists()


def test_login_rejects_open_redirect():
    from app.auth import safe_next
    assert safe_next("//evil.com") == "/" and safe_next("https://evil.com") == "/"
    assert safe_next("/artifacts/3?x=1") == "/artifacts/3?x=1"


def test_no_department_filter_matches_dashboard_key(client, login, db):
    user = login("u1", "홍길동", dept=None)
    client.post("/api/artifacts", json=ART)
    row = client.get("/api/dashboard").json()["byDepartment"][0]
    assert row["label"] == "미지정" and row["count"] == 1
    assert client.get("/api/artifacts", params={"department": row["key"]}).json()["total"] == 1
    assert user.department is None


def test_used_day_boundary_follows_configured_timezone(client, login, db, monkeypatch):
    """KST 00:30 은 UTC 로는 전날 15:30 이지만, 사용 기록 '오늘' 기준은 KST 날짜여야 합니다."""
    from datetime import timedelta

    from app.models import UsageEvent
    from app.routers import artifacts as mod

    user = login()
    aid = client.post("/api/artifacts", json=ART).json()["id"]
    kst_midnight = mod._today_start()
    assert kst_midnight.utcoffset() == timedelta(hours=9)
    # 어제(KST) 23:50 기록은 오늘 기록으로 치지 않습니다.
    db.add(UsageEvent(artifact_id=aid, user_id=user.id, kind="used", created_at=kst_midnight - timedelta(minutes=10)))
    db.commit()
    assert client.get(f"/api/artifacts/{aid}").json()["usedByMeToday"] is False
    assert client.post(f"/api/artifacts/{aid}/used").json() == {"useCount": 2}
