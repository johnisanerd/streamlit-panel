"""
CRM domain için SQLAlchemy ORM modelleri.
Master plan şemasına uygun: hotels, crm_users, user_events, curators, curated_hotels tabloları.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db import Base


class Hotel(Base):
    """Küratörlük sistemine eklenmiş oteller."""

    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    rating: Mapped[float | None] = mapped_column(Float)          # 1.0–5.0
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)   # 3, 4, 5
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    price_level: Mapped[str] = mapped_column(String(20), default="mid")  # budget | mid | luxury
    price_min: Mapped[float | None] = mapped_column(Float)                # USD/gece
    price_max: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    amenities: Mapped[str | None] = mapped_column(Text)           # JSON list
    profile_tags: Mapped[str | None] = mapped_column(Text)        # JSON list (uygun profiller)
    instagram_url: Mapped[str | None] = mapped_column(String(255))
    website_url: Mapped[str | None] = mapped_column(String(255))
    booking_url: Mapped[str | None] = mapped_column(String(255))
    whatsapp_url: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    events: Mapped[list["UserEvent"]] = relationship("UserEvent", back_populates="hotel")

    def __repr__(self) -> str:
        return f"<Hotel {self.id} {self.name!r} {self.city}/{self.district}>"


class CRMUser(Base):
    """
    CRM sistemindeki kullanıcılar.
    Sprint 1'deki genel `users` tablosundan ayrı; seyahat profili bilgisi taşır.
    """

    __tablename__ = "crm_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))           # kullanıcının bulunduğu şehir
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    preferred_budget: Mapped[str] = mapped_column(String(20), default="mid")  # budget | mid | luxury
    travel_type: Mapped[str | None] = mapped_column(String(50))
    age_range: Mapped[str] = mapped_column(String(10), default="25-34")
    device_type: Mapped[str] = mapped_column(String(20), default="mobile")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    events: Mapped[list["UserEvent"]] = relationship("UserEvent", back_populates="user")
    rfm_score: Mapped["RFMScore | None"] = relationship(
        "RFMScore", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CRMUser {self.id} {self.profile_type!r}>"


class UserEvent(Base):
    """Kullanıcı davranış olayları (tıklama, görüntüleme, favori vb.)."""

    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crm_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hotel_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source: Mapped[str] = mapped_column(String(50), default="web")  # web | mobile | campaign
    metadata_json: Mapped[str | None] = mapped_column(Text)          # JSON ek veri

    user: Mapped["CRMUser"] = relationship("CRMUser", back_populates="events")
    hotel: Mapped["Hotel | None"] = relationship("Hotel", back_populates="events")

    def __repr__(self) -> str:
        return f"<UserEvent {self.id} {self.event_type!r} user={self.user_id}>"


class Curator(Base):
    """Sisteme kayıtlı içerik küratörleri."""

    __tablename__ = "curators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    instagram_username: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    niche: Mapped[str | None] = mapped_column(String(100))  # ana uzmanlık alanı
    trust_score: Mapped[float] = mapped_column(Float, default=7.0)  # 1–10
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    curated: Mapped[list["CuratedHotel"]] = relationship("CuratedHotel", back_populates="curator")

    def __repr__(self) -> str:
        return f"<Curator {self.id} {self.name!r}>"


class CuratedHotel(Base):
    """Bir küratörün sisteme eklediği otel önerisi."""

    __tablename__ = "curated_hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("curators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hotel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_post_url: Mapped[str | None] = mapped_column(String(500))
    curator_note: Mapped[str | None] = mapped_column(Text)
    categories: Mapped[str | None] = mapped_column(Text)  # JSON list — predefined kategoriler
    tags: Mapped[str | None] = mapped_column(Text)        # JSON list — serbest etiketler
    score: Mapped[float] = mapped_column(Float, default=7.0)  # 1–10
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    curator: Mapped["Curator"] = relationship("Curator", back_populates="curated")
    hotel: Mapped["Hotel"] = relationship("Hotel")

    def __repr__(self) -> str:
        return f"<CuratedHotel {self.id} curator={self.curator_id} hotel={self.hotel_id}>"


class RFMScore(Base):
    """Kullanıcı RFM analiz skoru — her analiz çalışmasında üzerine yazılır."""

    __tablename__ = "rfm_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crm_users.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    monetary: Mapped[float] = mapped_column(Float, nullable=False)
    r_score: Mapped[int] = mapped_column(Integer, nullable=False)
    f_score: Mapped[int] = mapped_column(Integer, nullable=False)
    m_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rfm_segment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    user: Mapped["CRMUser"] = relationship("CRMUser", back_populates="rfm_score")

    def __repr__(self) -> str:
        return f"<RFMScore user={self.user_id} segment={self.rfm_segment!r}>"


class AutomationEvent(Base):
    """Gönderilen veya simüle edilen kampanya webhook olayları."""

    __tablename__ = "automation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    segment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_user_count: Mapped[int] = mapped_column(Integer, default=0)
    webhook_status: Mapped[str] = mapped_column(String(20), nullable=False)  # simulated|sent|failed
    payload_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    hotel: Mapped["Hotel | None"] = relationship("Hotel")

    def __repr__(self) -> str:
        return f"<AutomationEvent {self.id} {self.campaign_name!r} {self.webhook_status}>"


class BusinessAccount(Base):
    """İşletme sahiplerinin sisteme kayıtlı işletme hesapları."""

    __tablename__ = "business_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    owner_name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_email: Mapped[str | None] = mapped_column(String(255))
    owner_phone: Mapped[str | None] = mapped_column(String(50))
    google_maps_url: Mapped[str | None] = mapped_column(String(500))
    apify_raw_json: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    hotel: Mapped["Hotel"] = relationship("Hotel")

    def __repr__(self) -> str:
        return f"<BusinessAccount {self.id} owner={self.owner_name!r} hotel={self.hotel_id}>"


class InstagramPost(Base):
    """Bir otele ait Instagram gönderisi — sadece public veriler."""

    __tablename__ = "instagram_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_url: Mapped[str] = mapped_column(String(500), nullable=False)   # kaynak profil URL
    post_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    caption: Mapped[str | None] = mapped_column(Text)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    inferred_features: Mapped[str | None] = mapped_column(Text)  # JSON list
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    hotel: Mapped["Hotel"] = relationship("Hotel")
    comments: Mapped[list["InstagramComment"]] = relationship(
        "InstagramComment", back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InstagramPost {self.id} hotel={self.hotel_id}>"


class InstagramComment(Base):
    """Instagram gönderisine ait public yorum."""

    __tablename__ = "instagram_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instagram_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(100))
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    post: Mapped["InstagramPost"] = relationship("InstagramPost", back_populates="comments")

    def __repr__(self) -> str:
        return f"<InstagramComment {self.id} post={self.post_id}>"
