"""
İşletme onboarding servisi — Sprint 9

Apify Google Maps sonuçlarını hotels tablosuna eşleştirir/kaydeder
ve business_accounts tablosuna bağlar.
"""

import json
from difflib import SequenceMatcher

from src.crm.models import BusinessAccount, Hotel
from src.database.db import Base, engine, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_tables() -> None:
    """business_accounts tablosunu (yoksa) oluşturur."""
    Base.metadata.create_all(bind=engine)


# ─── Eşleştirme ───────────────────────────────────────────────────────────────

def find_existing_hotel(place: dict) -> Hotel | None:
    """
    Google Maps URL veya ad benzerliğine (≥ 0.85) göre mevcut oteli arar.
    Bulunamazsa None döndürür.
    """
    google_url = place.get("google_maps_url", "")
    name       = place.get("name", "").lower()

    try:
        with get_db() as db:
            # 1. google_maps_url → business_accounts üzerinden bul
            if google_url:
                account = (
                    db.query(BusinessAccount)
                    .filter(BusinessAccount.google_maps_url == google_url)
                    .first()
                )
                if account:
                    hotel = db.query(Hotel).filter(Hotel.id == account.hotel_id).first()
                    if hotel:
                        return hotel

            # 2. Otel adı benzerliği ≥ 0.85
            hotels = db.query(Hotel).filter(Hotel.is_active == True).all()
            for hotel in hotels:
                ratio = SequenceMatcher(None, name, hotel.name.lower()).ratio()
                if ratio >= 0.85:
                    return hotel

    except Exception as exc:
        logger.error("Otel eşleştirme hatası: %s", exc)

    return None


# ─── Otel oluşturma ───────────────────────────────────────────────────────────

def create_hotel_from_place(place: dict, extra: dict) -> int:
    """
    Apify yer verisinden hotels tablosuna yeni kayıt ekler.

    extra anahtarları: city, district, stars (int), price_level (str)

    Döner: hotel_id
    """
    try:
        with get_db() as db:
            hotel = Hotel(
                name=place.get("name", "Bilinmiyor"),
                city=extra.get("city", ""),
                district=extra.get("district", ""),
                address=place.get("address", ""),
                rating=place.get("rating"),
                review_count=int(place.get("review_count") or 0),
                stars=int(extra.get("stars", 4)),
                latitude=place.get("latitude"),
                longitude=place.get("longitude"),
                price_level=extra.get("price_level", "mid"),
                website_url=place.get("website") or None,
                phone=place.get("phone") or None,
                is_active=True,
            )
            db.add(hotel)
            db.commit()
            return hotel.id
    except Exception as exc:
        logger.error("Otel oluşturulamadı: %s", exc)
        raise


# ─── İşletme hesabı ───────────────────────────────────────────────────────────

def register_business_account(
    hotel_id: int,
    owner_name: str,
    owner_email: str | None,
    owner_phone: str | None,
    place: dict,
) -> int:
    """
    BusinessAccount kaydı oluşturur; mevcut varsa günceller.

    Döner: account_id
    """
    try:
        with get_db() as db:
            existing = (
                db.query(BusinessAccount)
                .filter(BusinessAccount.hotel_id == hotel_id)
                .first()
            )
            if existing:
                existing.owner_name     = owner_name
                existing.owner_email    = owner_email
                existing.owner_phone    = owner_phone
                existing.google_maps_url = place.get("google_maps_url", "")
                existing.apify_raw_json  = json.dumps(place, ensure_ascii=False)
                db.commit()
                return existing.id

            account = BusinessAccount(
                hotel_id=hotel_id,
                owner_name=owner_name,
                owner_email=owner_email,
                owner_phone=owner_phone,
                google_maps_url=place.get("google_maps_url", ""),
                apify_raw_json=json.dumps(place, ensure_ascii=False),
                verified=False,
            )
            db.add(account)
            db.commit()
            return account.id
    except Exception as exc:
        logger.error("BusinessAccount kaydedilemedi: %s", exc)
        raise


# ─── Liste ────────────────────────────────────────────────────────────────────

def get_registered_businesses() -> list[dict]:
    """Kayıtlı işletme hesaplarını otel bilgileriyle döndürür."""
    try:
        with get_db() as db:
            rows = (
                db.query(
                    BusinessAccount.id,
                    BusinessAccount.owner_name,
                    BusinessAccount.owner_email,
                    BusinessAccount.verified,
                    BusinessAccount.created_at,
                    Hotel.name.label("hotel_name"),
                    Hotel.city,
                    Hotel.district,
                    Hotel.rating,
                )
                .join(Hotel, BusinessAccount.hotel_id == Hotel.id)
                .order_by(BusinessAccount.created_at.desc())
                .all()
            )
        return [r._asdict() for r in rows]
    except Exception as exc:
        logger.error("İşletme listesi yüklenemedi: %s", exc)
        return []
