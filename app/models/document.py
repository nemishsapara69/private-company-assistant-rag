from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    doc_type: Mapped[str] = mapped_column(String(50), index=True)
    sensitivity: Mapped[str] = mapped_column(String(50), default="internal")
    owner: Mapped[str] = mapped_column(String(100), index=True)
    allowed_roles: Mapped[str] = mapped_column(Text, default="employee,manager,hr,it,admin")
    source_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))