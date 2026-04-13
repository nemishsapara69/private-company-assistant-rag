from fastapi.testclient import TestClient

from app.main import app
from app.db.bootstrap import init_db, seed_demo_users
from app.db.session import SessionLocal


def _ensure_db_ready() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()


_ensure_db_ready()


client = TestClient(app)


def _login(username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_document(admin_token: str, title: str) -> int:
    response = client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": title,
            "department": "hr",
            "doc_type": "policy",
            "sensitivity": "internal",
            "owner": "HR Team",
            "allowed_roles": ["employee", "manager", "hr", "it", "admin"],
            "source_path": "",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_document_approval_workflow() -> None:
    admin_token = _login("super_admin", "admin123")
    doc_id = _create_document(admin_token, "Workflow Approval Doc")

    create_resp = client.post(
        "/api/v1/workflows/document-approvals",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"document_id": doc_id, "reviewer": "hr_admin", "note": "Please approve"},
    )
    assert create_resp.status_code == 200
    approval_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    decision_resp = client.post(
        f"/api/v1/workflows/document-approvals/{approval_id}/decision",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"approve": True, "comment": "Looks good"},
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "approved"


def test_manual_ticket_workflow() -> None:
    user_token = _login("hr_admin", "hr123")
    admin_token = _login("super_admin", "admin123")

    create_resp = client.post(
        "/api/v1/workflows/tickets",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "module": "hr",
            "question": "Need manual support for special leave exception",
            "reason": "manual_request",
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["auto_created"] is False

    list_resp = client.get(
        "/api/v1/workflows/tickets",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_policy_notification_workflow() -> None:
    admin_token = _login("super_admin", "admin123")
    doc_id = _create_document(admin_token, "Workflow Notification Doc")

    notify_resp = client.post(
        "/api/v1/workflows/policy-notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "document_id": doc_id,
            "message": "Policy updated for remote access rules",
            "target_roles": ["employee", "manager"],
        },
    )
    assert notify_resp.status_code == 200
    assert notify_resp.json()["status"] == "sent"


def test_low_confidence_chat_creates_auto_ticket() -> None:
    user_token = _login("hr_admin", "hr123")
    admin_token = _login("super_admin", "admin123")

    chat_resp = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"question": "zxqv never in docs 918273", "module": "hr"},
    )
    assert chat_resp.status_code == 200

    tickets_resp = client.get(
        "/api/v1/workflows/tickets",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert tickets_resp.status_code == 200
    assert any(
        ticket["reason"] == "low_confidence_unresolved" and ticket["auto_created"] is True
        for ticket in tickets_resp.json()
    )
