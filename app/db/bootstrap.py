from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine
from app.models import User


DEMO_USERS = [
    {"username": "alice", "password": "alice123", "role": "employee", "department": "general"},
    {"username": "bob", "password": "bob123", "role": "manager", "department": "operations"},
    {"username": "hr_admin", "password": "hr123", "role": "hr", "department": "hr"},
    {"username": "it_admin", "password": "it123", "role": "it", "department": "it"},
    {"username": "super_admin", "password": "admin123", "role": "admin", "department": "admin"},
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)



def seed_demo_users(db: Session) -> None:
    existing = db.execute(select(User.id)).first()
    if existing:
        return

    for user in DEMO_USERS:
        db.add(
            User(
                username=user["username"],
                password_hash=get_password_hash(user["password"]),
                role=user["role"],
                department=user["department"],
            )
        )

    db.commit()
