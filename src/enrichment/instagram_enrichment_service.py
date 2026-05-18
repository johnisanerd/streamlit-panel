"""
Instagram zenginleştirme servisi — Sprint 10

Apify'den gelen public Instagram post verilerini veritabanına kaydeder,
caption analizinden otel özelliklerini çıkarır ve hotels.amenities'i günceller.
"""

import json

from src.crm.models import Hotel, InstagramComment, InstagramPost
from src.database.db import Base, engine, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Özellik çıkarımı — anahtar kelime sözlüğü ───────────────────────────────

FEATURE_KEYWORDS: dict[str, str] = {
    "havuz":          "Yüzme Havuzu",
    "pool":           "Yüzme Havuzu",
    "spa":            "Spa",
    "hamam":          "Hamam",
    "sauna":          "Sauna",
    "deniz manzara":  "Deniz Manzarası",
    "sea view":       "Deniz Manzarası",
    "bosphorus":      "Boğaz Manzarası",
    "boğaz":          "Boğaz Manzarası",
    "restoran":       "Restoran",
    "restaurant":     "Restoran",
    "kahvaltı":       "Kahvaltı",
    "breakfast":      "Kahvaltı",
    "wifi":           "WiFi",
    "otopark":        "Otopark",
    "parking":        "Otopark",
    "balkon":         "Balkon",
    "balcony":        "Balkon",
    "plaj":           "Plaj Erişimi",
    "beach":          "Plaj Erişimi",
    "fitness":        "Fitness Merkezi",
    "gym":            "Fitness Merkezi",
    "suit":           "Suit Oda",
    "suite":          "Suit Oda",
    "romantik":       "Romantik Paket",
    "romantic":       "Romantik Paket",
    "balayı":         "Balayı Paketi",
    "honeymoon":      "Balayı Paketi",
    "yoga":           "Yoga",
    "wellness":       "Wellness",
    "transfer":       "Havalimanı Transferi",
    "airport":        "Havalimanı Transferi",
    "çocuk kulübü":   "Çocuk Kulübü",
    "kids club":      "Çocuk Kulübü",
    "toplantı":       "Toplantı Odası",
    "meeting":        "Toplantı Odası",
    "aile":           "Aile Odaları",
}


def infer_features(caption: str) -> list[str]:
    """Caption metninden anahtar kelime eşleştirme ile otel özelliklerini çıkarır."""
    text = (caption or "").lower()
    found: set[str] = set()
    for keyword, feature in FEATURE_KEYWORDS.items():
        if keyword in text:
            found.add(feature)
    return sorted(found)


# ─── Tablo kurulumu ───────────────────────────────────────────────────────────

def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def get_hotel_instagram_url(hotel_id: int) -> str:
    """hotels tablosundaki instagram_url alanını döndürür."""
    try:
        with get_db() as db:
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            return hotel.instagram_url or "" if hotel else ""
    except Exception as exc:
        logger.error("Instagram URL yüklenemedi: %s", exc)
        return ""


# ─── Kaydetme ─────────────────────────────────────────────────────────────────

def save_instagram_posts(hotel_id: int, instagram_url: str, posts: list[dict]) -> int:
    """
    Scraping sonuçlarını instagram_posts + instagram_comments tablolarına kaydeder.
    Aynı post_url varsa atlar (unique kısıtı). Döner: yeni kaydedilen sayı.
    """
    saved = 0
    try:
        with get_db() as db:
            existing_urls: set[str] = {
                r[0]
                for r in db.query(InstagramPost.post_url)
                .filter(InstagramPost.hotel_id == hotel_id)
                .all()
            }

            for post in posts:
                post_url = post.get("post_url", "")
                if not post_url or post_url in existing_urls:
                    continue

                features = infer_features(post.get("caption", ""))
                ig_post = InstagramPost(
                    hotel_id=hotel_id,
                    instagram_url=instagram_url,
                    post_url=post_url,
                    caption=post.get("caption") or None,
                    likes_count=int(post.get("likes_count") or 0),
                    comments_count=int(post.get("comments_count") or 0),
                    timestamp=post.get("timestamp"),
                    inferred_features=json.dumps(features, ensure_ascii=False) if features else None,
                )
                db.add(ig_post)
                db.flush()  # id al

                for c in post.get("comments") or []:
                    text = c.get("comment_text", "").strip()
                    if text:
                        db.add(InstagramComment(
                            post_id=ig_post.id,
                            username=c.get("username") or None,
                            comment_text=text,
                        ))

                existing_urls.add(post_url)
                saved += 1

            db.commit()
    except Exception as exc:
        logger.error("Instagram post kaydı hatası: %s", exc)
        raise

    return saved


# ─── Okuma ────────────────────────────────────────────────────────────────────

def get_hotel_posts(hotel_id: int) -> list[dict]:
    """Bir otele ait kaydedilmiş Instagram postlarını döndürür."""
    try:
        with get_db() as db:
            posts = (
                db.query(InstagramPost)
                .filter(InstagramPost.hotel_id == hotel_id)
                .order_by(InstagramPost.scraped_at.desc())
                .all()
            )
            result = []
            for p in posts:
                comments = [
                    {"username": c.username, "comment_text": c.comment_text}
                    for c in p.comments
                ]
                result.append({
                    "id":               p.id,
                    "post_url":         p.post_url,
                    "caption":          p.caption or "",
                    "likes_count":      p.likes_count,
                    "comments_count":   p.comments_count,
                    "timestamp":        p.timestamp,
                    "inferred_features": json.loads(p.inferred_features) if p.inferred_features else [],
                    "scraped_at":       p.scraped_at,
                    "comments":         comments,
                })
            return result
    except Exception as exc:
        logger.error("Hotel postları yüklenemedi: %s", exc)
        return []


def get_aggregate_features(hotel_id: int) -> list[str]:
    """Otelin tüm postlarından çıkarılan özellik birleşimini döndürür."""
    posts = get_hotel_posts(hotel_id)
    features: set[str] = set()
    for p in posts:
        features.update(p.get("inferred_features") or [])
    return sorted(features)


# ─── Otele uygula ─────────────────────────────────────────────────────────────

def apply_features_to_hotel(hotel_id: int, features: list[str]) -> bool:
    """
    Çıkarılan özellikleri hotels.amenities alanına ekler (mevcut değerleri korur).
    Döner: True başarı, False hata.
    """
    if not features:
        return True
    try:
        with get_db() as db:
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            if not hotel:
                return False

            existing: list[str] = []
            if hotel.amenities:
                try:
                    existing = json.loads(hotel.amenities)
                except Exception:
                    existing = []

            merged = sorted(set(existing) | set(features))
            hotel.amenities = json.dumps(merged, ensure_ascii=False)
            db.commit()
        return True
    except Exception as exc:
        logger.error("Hotel amenities güncellenemedi: %s", exc)
        return False
