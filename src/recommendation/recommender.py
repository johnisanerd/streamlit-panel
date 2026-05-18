"""
İçerik tabanlı otel öneri sistemi — Sprint 11

Cosine similarity kullanılarak kullanıcı profiline en uygun oteller sıralanır.
Model basit ve açıklanabilir: 9 boyutlu özellik vektörü + numpy dot product.
"""

import json

import numpy as np
import pandas as pd

from src.crm.models import Hotel, UserEvent
from src.database.db import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

PROFILE_TAGS = [
    "luxury_traveler", "family_vacation", "budget_traveler",
    "honeymoon", "business_traveler", "wellness_spa",
]

PRICE_ENCODE = {"budget": 0.0, "mid": 0.5, "luxury": 1.0}

PROFILE_TR = {
    "luxury_traveler":   "💎 Lüks",
    "family_vacation":   "👨‍👩‍👧 Aile",
    "budget_traveler":   "💰 Ekonomik",
    "honeymoon":         "💑 Balayı",
    "business_traveler": "💼 İş Seyahati",
    "wellness_spa":      "🧘 Wellness & Spa",
}

# Kullanıcı profil tipine göre tercih vektörleri (9 boyut, sıralama aşağıda)
# [price_level, rating, stars, lux, fam, budget, honey, biz, wellness]
_PROFILE_PREFS: dict[str, list[float]] = {
    "luxury_traveler":   [1.0, 0.9, 1.0,  1.0, 0.0, 0.0, 0.3, 0.2, 0.4],
    "family_vacation":   [0.5, 0.7, 0.5,  0.1, 1.0, 0.2, 0.1, 0.0, 0.1],
    "budget_traveler":   [0.0, 0.5, 0.0,  0.0, 0.2, 1.0, 0.0, 0.3, 0.0],
    "honeymoon":         [0.8, 0.9, 0.8,  0.5, 0.0, 0.0, 1.0, 0.0, 0.3],
    "business_traveler": [0.7, 0.8, 0.7,  0.2, 0.0, 0.0, 0.0, 1.0, 0.1],
    "wellness_spa":      [0.7, 0.8, 0.6,  0.3, 0.0, 0.0, 0.2, 0.0, 1.0],
}

_BUDGET_PRICE = {"budget": 0.0, "mid": 0.5, "luxury": 1.0}


# ─── Özellik mühendisliği ─────────────────────────────────────────────────────

def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _hotel_to_vector(hotel: Hotel) -> np.ndarray:
    """
    Bir oteli 9 boyutlu özellik vektörüne dönüştürür.
    Sıra: price_level, rating, stars, [6 profil etiketi]
    """
    price  = PRICE_ENCODE.get(hotel.price_level or "mid", 0.5)
    rating = (hotel.rating or 3.5) / 5.0
    stars  = ((hotel.stars or 4) - 3) / 2.0  # 3→0, 4→0.5, 5→1.0

    tags = _parse_json_list(hotel.profile_tags)
    tag_vec = [1.0 if t in tags else 0.0 for t in PROFILE_TAGS]

    return np.array([price, rating, stars] + tag_vec, dtype=float)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 1e-9 else 0.0


# ─── Veri yükleme ─────────────────────────────────────────────────────────────

def load_hotels_df() -> pd.DataFrame:
    """Aktif otelleri ve hesaplanan özellik vektörlerini DataFrame olarak döndürür."""
    try:
        with get_db() as db:
            hotels = db.query(Hotel).filter(Hotel.is_active == True).all()
        if not hotels:
            return pd.DataFrame()

        rows = []
        for h in hotels:
            vec = _hotel_to_vector(h)
            rows.append({
                "hotel_id":    h.id,
                "name":        h.name,
                "city":        h.city,
                "district":    h.district,
                "stars":       h.stars,
                "rating":      h.rating or 0.0,
                "review_count": h.review_count,
                "price_level": h.price_level,
                "price_min":   h.price_min,
                "price_max":   h.price_max,
                "profile_tags": _parse_json_list(h.profile_tags),
                "amenities":   _parse_json_list(h.amenities),
                "feature_vec": vec,
            })
        return pd.DataFrame(rows)
    except Exception as exc:
        logger.error("Otel verisi yüklenemedi: %s", exc)
        return pd.DataFrame()


def _load_user_event_hotel_ids(user_id: int) -> list[int]:
    """Kullanıcının etkileştiği otel ID'lerini döndürür."""
    try:
        with get_db() as db:
            rows = (
                db.query(UserEvent.hotel_id)
                .filter(UserEvent.user_id == user_id, UserEvent.hotel_id.isnot(None))
                .distinct()
                .all()
            )
        return [r[0] for r in rows]
    except Exception:
        return []


# ─── Öneri fonksiyonları ──────────────────────────────────────────────────────

def recommend_for_profile(
    profile_type: str,
    preferred_budget: str = "mid",
    city: str | None = None,
    top_n: int = 6,
) -> pd.DataFrame:
    """
    Kullanıcı profiline göre cosine similarity ile otel önerir.

    Döner: hotel_id, name, city, district, stars, rating, price_level,
           profile_tags, similarity (0-1), rank
    """
    df = load_hotels_df()
    if df.empty:
        return pd.DataFrame()

    if city and city != "Tüm Şehirler":
        df = df[df["city"] == city]
    if df.empty:
        return pd.DataFrame()

    # Kullanıcı tercih vektörü — profil + bütçe ağırlıklandırması
    pref = np.array(_PROFILE_PREFS.get(profile_type, _PROFILE_PREFS["budget_traveler"]), dtype=float)
    budget_price = _BUDGET_PRICE.get(preferred_budget, 0.5)
    pref[0] = pref[0] * 0.6 + budget_price * 0.4  # price_level bileşenine bütçeyi karıştır

    df = df.copy()
    df["similarity"] = df["feature_vec"].apply(lambda v: _cosine_similarity(pref, v))
    df = df.sort_values("similarity", ascending=False).head(top_n).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["similarity_pct"] = (df["similarity"] * 100).round(1)

    return df[["rank", "hotel_id", "name", "city", "district", "stars", "rating",
               "review_count", "price_level", "price_min", "price_max",
               "profile_tags", "amenities", "similarity", "similarity_pct"]]


def find_similar_hotels(hotel_id: int, top_n: int = 4) -> pd.DataFrame:
    """
    Verilen otele en benzer diğer otelleri döndürür (cosine similarity).
    """
    df = load_hotels_df()
    if df.empty or hotel_id not in df["hotel_id"].values:
        return pd.DataFrame()

    target_vec = df.loc[df["hotel_id"] == hotel_id, "feature_vec"].iloc[0]
    others = df[df["hotel_id"] != hotel_id].copy()
    others["similarity"] = others["feature_vec"].apply(
        lambda v: _cosine_similarity(target_vec, v)
    )
    others = others.sort_values("similarity", ascending=False).head(top_n).reset_index(drop=True)
    others["similarity_pct"] = (others["similarity"] * 100).round(1)

    return others[["hotel_id", "name", "city", "stars", "rating",
                   "price_level", "profile_tags", "similarity_pct"]]


def recommend_from_history(user_id: int, top_n: int = 6) -> pd.DataFrame:
    """
    Kullanıcının event geçmişindeki otellerin ortalama vektörüne benzer oteller önerir.
    Event geçmişi yoksa boş DataFrame döner.
    """
    df = load_hotels_df()
    if df.empty:
        return pd.DataFrame()

    seen_ids = _load_user_event_hotel_ids(user_id)
    if not seen_ids:
        return pd.DataFrame()

    seen_vecs = df[df["hotel_id"].isin(seen_ids)]["feature_vec"].tolist()
    if not seen_vecs:
        return pd.DataFrame()

    history_vec = np.mean(np.stack(seen_vecs), axis=0)

    unseen = df[~df["hotel_id"].isin(seen_ids)].copy()
    if unseen.empty:
        return pd.DataFrame()

    unseen["similarity"] = unseen["feature_vec"].apply(
        lambda v: _cosine_similarity(history_vec, v)
    )
    unseen = unseen.sort_values("similarity", ascending=False).head(top_n).reset_index(drop=True)
    unseen["rank"] = unseen.index + 1
    unseen["similarity_pct"] = (unseen["similarity"] * 100).round(1)

    return unseen[["rank", "hotel_id", "name", "city", "district", "stars", "rating",
                   "review_count", "price_level", "profile_tags", "amenities", "similarity_pct"]]
