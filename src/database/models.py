"""
SQLAlchemy ORM modelleri.
Kullanıcı, içerik ve öneri verilerini temsil eden tablolar.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db import Base


class User(Base):
    """Sisteme kayıtlı kullanıcılar."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    interactions: Mapped[list["Interaction"]] = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


class Item(Base):
    """Önerilebilecek içerik veya ürünler."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON string olarak saklanır
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    interactions: Mapped[list["Interaction"]] = relationship("Interaction", back_populates="item")

    def __repr__(self) -> str:
        return f"<Item id={self.id} title={self.title!r}>"


class Interaction(Base):
    """Kullanıcı-içerik etkileşimleri (tıklama, beğeni, derecelendirme vb.)."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # click, like, rate, view
    rating: Mapped[float | None] = mapped_column(Float)  # 1.0 - 5.0 arası, opsiyonel
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="interactions")
    item: Mapped["Item"] = relationship("Item", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<Interaction user={self.user_id} item={self.item_id} type={self.interaction_type!r}>"
