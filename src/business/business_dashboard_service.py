"""
İşletme paneli veri servisi.

user_events tablosundan KPI, grafik ve öneri verilerini hesaplar.
Tüm fonksiyonlar pandas DataFrame döndürür — saf Python, Streamlit bağımlılığı yok.
"""

from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func

from src.crm.models import CRMUser, Hotel, UserEvent
from src.database.db import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

# RFM proxy ağırlıkları (master plan ile aynı)
EVENT_VALUE: dict[str, int] = {
    "reservation_click": 100,
    "whatsapp_click":     70,
    "website_redirect":   50,
    "favorite_added":     20,
    "hotel_view":          5,
    "filter_used":         2,
    "campaign_click":     30,
}

HIGH_VALUE_EVENTS = {"reservation_click", "whatsapp_click", "website_redirect"}

PROFILE_TR: dict[str, str] = {
    "luxury_traveler":   "💎 Lüks",
    "family_vacation":   "👨‍👩‍👧 Aile",
    "budget_traveler":   "💰 Ekonomik",
    "honeymoon":         "💑 Balayı",
    "business_traveler": "💼 İş Seyahati",
    "wellness_spa":      "🧘 Spa & Wellness",
}

EVENT_TR: dict[str, str] = {
    "hotel_view":        "Görüntülenme",
    "favorite_added":    "Favoriye Ekleme",
    "reservation_click": "Rezervasyon Tıklaması",
    "whatsapp_click":    "WhatsApp Tıklaması",
    "website_redirect":  "Website Yönlendirmesi",
    "filter_used":       "Filtre Kullanımı",
    "campaign_click":    "Kampanya Tıklaması",
}

# ─── Ham veri yükleme ─────────────────────────────────────────────────────────

def load_hotel_events(hotel_id: int, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """
    Belirli bir otel için tarih aralığındaki tüm user_event'leri DataFrame olarak döndürür.

    Sütunlar: event_type, event_date, profile_type, age_range, device_type, metadata_json
    """
    try:
        with get_db() as db:
            rows = (
                db.query(
                    UserEvent.event_type,
                    UserEvent.event_date,
                    UserEvent.metadata_json,
                    CRMUser.profile_type,
                    CRMUser.age_range,
                    CRMUser.device_type,
                )
                .join(CRMUser, UserEvent.user_id == CRMUser.id)
                .filter(UserEvent.hotel_id == hotel_id)
                .filter(UserEvent.event_date >= start_dt)
                .filter(UserEvent.event_date <= end_dt)
                .all()
            )
        if not rows:
            return pd.DataFrame(columns=["event_type", "event_date", "profile_type",
                                         "age_range", "device_type", "metadata_json"])
        df = pd.DataFrame([r._asdict() for r in rows])
        df["event_date"] = pd.to_datetime(df["event_date"])
        df["date"] = df["event_date"].dt.date
        return df
    except Exception as exc:
        logger.error("Hotel events yüklenemedi (id=%d): %s", hotel_id, exc)
        return pd.DataFrame()


def load_all_hotel_events(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """
    Tüm oteller için tarih aralığındaki event sayılarını döndürür.

    Sütunlar: hotel_id, hotel_name, city, price_level, event_type, count
    """
    try:
        with get_db() as db:
            rows = (
                db.query(
                    UserEvent.hotel_id,
                    UserEvent.event_type,
                    Hotel.name.label("hotel_name"),
                    Hotel.city,
                    Hotel.price_level,
                )
                .join(Hotel, UserEvent.hotel_id == Hotel.id)
                .filter(UserEvent.hotel_id.isnot(None))
                .filter(UserEvent.event_date >= start_dt)
                .filter(UserEvent.event_date <= end_dt)
                .all()
            )
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([r._asdict() for r in rows])
    except Exception as exc:
        logger.error("All hotel events yüklenemedi: %s", exc)
        return pd.DataFrame()


def load_hotels_in_city(hotel_id: int) -> list[int]:
    """Aynı şehirdeki aktif otel id'lerini döndürür (seçili otel dahil)."""
    try:
        with get_db() as db:
            city = db.query(Hotel.city).filter(Hotel.id == hotel_id).scalar()
            ids  = [r.id for r in db.query(Hotel.id).filter(Hotel.city == city).all()]
        return ids
    except Exception as exc:
        logger.error("Şehir otelleri yüklenemedi: %s", exc)
        return [hotel_id]


# ─── KPI hesaplama ────────────────────────────────────────────────────────────

def calc_kpis(df: pd.DataFrame) -> dict[str, float]:
    """
    Tek bir otelin event DataFrame'inden KPI değerlerini hesaplar.

    Dönen anahtarlar:
        views, favorites, reservations, whatsapp, website, conversion_rate
    """
    if df.empty:
        return dict(views=0, favorites=0, reservations=0,
                    whatsapp=0, website=0, conversion_rate=0.0)

    c = df["event_type"].value_counts().to_dict()
    views        = c.get("hotel_view",        0)
    favorites    = c.get("favorite_added",    0)
    reservations = c.get("reservation_click", 0)
    whatsapp     = c.get("whatsapp_click",    0)
    website      = c.get("website_redirect",  0)
    conversion   = round((reservations + whatsapp) / views * 100, 1) if views else 0.0

    return dict(
        views=views,
        favorites=favorites,
        reservations=reservations,
        whatsapp=whatsapp,
        website=website,
        conversion_rate=conversion,
    )


# ─── Grafik verisi ────────────────────────────────────────────────────────────

def calc_daily_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Günlük event sayısı trendi.

    Dönüş: date | event_type_tr | count
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "Event Tipi", "Sayı"])

    # Sadece görsel olarak anlamlı event tipleri
    keep = {"hotel_view", "favorite_added", "reservation_click", "whatsapp_click", "website_redirect"}
    sub  = df[df["event_type"].isin(keep)].copy()

    daily = (
        sub.groupby(["date", "event_type"])
        .size()
        .reset_index(name="Sayı")
    )
    daily["Event Tipi"] = daily["event_type"].map(lambda x: EVENT_TR.get(x, x))
    return daily[["date", "Event Tipi", "Sayı"]].rename(columns={"date": "Tarih"})


def calc_event_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Event tipi dağılımı (tüm tipler).

    Dönüş: event_type_tr | count | pct
    """
    if df.empty:
        return pd.DataFrame(columns=["Event Tipi", "Sayı", "Oran (%)"])

    dist = df["event_type"].value_counts().reset_index()
    dist.columns = ["event_type", "Sayı"]
    dist["Event Tipi"] = dist["event_type"].map(lambda x: EVENT_TR.get(x, x))
    dist["Oran (%)"]   = (dist["Sayı"] / dist["Sayı"].sum() * 100).round(1)
    return dist[["Event Tipi", "Sayı", "Oran (%)"]].sort_values("Sayı", ascending=False)


def calc_profile_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Etkileşim yapan kullanıcıların profil dağılımı.

    Dönüş: Profil | Sayı
    """
    if df.empty or "profile_type" not in df.columns:
        return pd.DataFrame(columns=["Profil", "Sayı"])

    dist = df["profile_type"].value_counts().reset_index()
    dist.columns = ["profile_type", "Sayı"]
    dist["Profil"] = dist["profile_type"].map(lambda x: PROFILE_TR.get(x, x))
    return dist[["Profil", "Sayı"]]


def calc_top_hotels(all_df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """
    Tüm dönemdeki en çok etkileşim alan oteller (total event count).

    Dönüş: hotel_name | city | total | hotel_view | reservation_click
    """
    if all_df.empty:
        return pd.DataFrame()

    pivot = (
        all_df.groupby(["hotel_id", "hotel_name", "city", "event_type"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    pivot["toplam"] = pivot.drop(columns=["hotel_id", "hotel_name", "city"]).sum(axis=1)
    pivot = pivot.sort_values("toplam", ascending=False).head(limit)

    cols = {"hotel_name": "Otel", "city": "Şehir", "toplam": "Toplam Etkileşim"}
    for et in ["hotel_view", "reservation_click", "favorite_added"]:
        if et in pivot.columns:
            cols[et] = EVENT_TR.get(et, et)

    return pivot.rename(columns=cols)[[c for c in cols.values() if c in pivot.rename(columns=cols).columns]]


def calc_competitor_comparison(hotel_id: int, all_df: pd.DataFrame) -> pd.DataFrame:
    """
    Seçili otel vs aynı şehirdeki rakiplerin hotel_view ve reservation_click karşılaştırması.

    Dönüş: Otel | Görüntülenme | Rezervasyon | Favori | Dönüşüm (%)
    """
    if all_df.empty:
        return pd.DataFrame()

    city_hotels = load_hotels_in_city(hotel_id)
    sub = all_df[all_df["hotel_id"].isin(city_hotels)]

    if sub.empty:
        return pd.DataFrame()

    piv = (
        sub.groupby(["hotel_id", "hotel_name", "event_type"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in ["hotel_view", "reservation_click", "favorite_added", "whatsapp_click"]:
        if col not in piv.columns:
            piv[col] = 0

    piv["Dönüşüm (%)"] = (
        (piv["reservation_click"] + piv["whatsapp_click"]) / piv["hotel_view"].replace(0, 1) * 100
    ).round(1)

    piv["Seçili"] = piv["hotel_id"] == hotel_id
    piv = piv.sort_values(["Seçili", "hotel_view"], ascending=[False, False])

    return piv.rename(columns={
        "hotel_name":        "Otel",
        "hotel_view":        "Görüntülenme",
        "reservation_click": "Rezervasyon",
        "favorite_added":    "Favori",
        "whatsapp_click":    "WhatsApp",
    })[["Otel", "Görüntülenme", "Rezervasyon", "Favori", "WhatsApp", "Dönüşüm (%)", "Seçili"]]


# ─── Öneri motoru ─────────────────────────────────────────────────────────────

def calc_recommendations(hotel_id: int, df: pd.DataFrame, all_df: pd.DataFrame) -> dict[str, str]:
    """
    Basit kural tabanlı 3 öneri üretir.

    Döner:
        segment:  hangi profil segmentine kampanya yapılmalı
        feature:  hangi özellik öne çıkarılmalı
        cta:      hangi CTA daha iyi çalışıyor
    """
    recs: dict[str, str] = {
        "segment": "Veri yetersiz — daha fazla etkileşim bekleniyor.",
        "feature": "Veri yetersiz — daha fazla etkileşim bekleniyor.",
        "cta":     "Veri yetersiz — daha fazla etkileşim bekleniyor.",
    }

    if df.empty:
        return recs

    # ── 1. En iyi kampanya segmenti ───────────────────────────────────────────
    # Görüntülenme yüksek ama dönüşüm düşük olan profil → potansiyel hedef
    if "profile_type" in df.columns:
        prof_stats = (
            df.groupby("profile_type")["event_type"]
            .apply(lambda s: pd.Series({
                "views": (s == "hotel_view").sum(),
                "conversions": s.isin(HIGH_VALUE_EVENTS).sum(),
            }))
            .unstack(fill_value=0)
        )
        if not prof_stats.empty and "views" in prof_stats.columns:
            prof_stats = prof_stats[prof_stats["views"] >= 3].copy()
            if not prof_stats.empty:
                prof_stats["conv_rate"] = prof_stats["conversions"] / prof_stats["views"].replace(0, 1)
                worst = prof_stats["conv_rate"].idxmin()
                best_views = prof_stats["views"].idxmax()
                if worst and best_views:
                    target = worst if prof_stats.loc[worst, "views"] >= 3 else best_views
                    tr_name = PROFILE_TR.get(target, target)
                    conv_pct = round(prof_stats.loc[target, "conv_rate"] * 100, 1)
                    recs["segment"] = (
                        f"**{tr_name}** segmenti bu oteli görüntülüyor "
                        f"(%{conv_pct} dönüşüm) — e-posta veya kampanya hedefi olabilir."
                    )

    # ── 2. Öne çıkarılacak özellik ────────────────────────────────────────────
    # Dönüşüm yapan kullanıcıların profil tipine göre tercih ettikleri özellik
    PROFILE_FEATURE_HINT = {
        "luxury_traveler":   "spa ve özel plaj erişimi",
        "family_vacation":   "çocuk kulübü ve havuz",
        "budget_traveler":   "uygun fiyat ve erken rezervasyon indirimleri",
        "honeymoon":         "romantik paketler ve deniz manzaralı oda",
        "business_traveler": "hızlı WiFi ve toplantı odası",
        "wellness_spa":      "hamam, yoga ve wellness paketleri",
    }
    if "profile_type" in df.columns:
        converters = df[df["event_type"].isin(HIGH_VALUE_EVENTS)]["profile_type"]
        if not converters.empty:
            top_profile = converters.value_counts().idxmax()
            hint = PROFILE_FEATURE_HINT.get(top_profile, "temel olanaklar")
            recs["feature"] = (
                f"Dönüşüm yapan kullanıcıların çoğu **{PROFILE_TR.get(top_profile, top_profile)}** "
                f"profilinde. Listelemenizde **{hint}** özelliklerini öne çıkarın."
            )

    # ── 3. En iyi CTA ─────────────────────────────────────────────────────────
    c = df["event_type"].value_counts().to_dict()
    views = c.get("hotel_view", 1)
    cta_rates = {
        "Rezervasyon Butonu":  c.get("reservation_click", 0) / views,
        "WhatsApp Butonu":     c.get("whatsapp_click",    0) / views,
        "Website Yönlendirme": c.get("website_redirect",  0) / views,
    }
    if any(v > 0 for v in cta_rates.values()):
        best_cta  = max(cta_rates, key=cta_rates.get)
        best_rate = round(cta_rates[best_cta] * 100, 1)
        worst_cta = min(cta_rates, key=cta_rates.get)
        recs["cta"] = (
            f"**{best_cta}** en yüksek dönüşüm oranına sahip (%{best_rate}). "
            f"**{worst_cta}** görünürlüğü artırılabilir."
        )

    return recs
