"""
RFM analizi — Sprint 7

Kullanıcı davranış verilerinden Recency, Frequency, Monetary skorları hesaplar,
segmentler atar ve rfm_scores tablosuna kaydeder.
"""

from datetime import datetime

import pandas as pd

from src.crm.models import CRMUser, RFMScore, UserEvent
from src.database.db import Base, engine, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

MONETARY_WEIGHTS: dict[str, float] = {
    "reservation_click": 100,
    "whatsapp_click":     70,
    "website_redirect":   50,
    "favorite_added":     20,
    "hotel_view":          5,
    "campaign_click":     30,
    "filter_used":         2,
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

SEGMENT_CAMPAIGNS: dict[str, str] = {
    "Champions":           "VIP ayrıcalıkları ve özel indirimler sunun.",
    "Loyal Customers":     "Sadakat programına davet edin; erken rezervasyon fırsatı verin.",
    "Potential Loyalists": "Özel tekliflerle sık kullanımı teşvik edin.",
    "New Customers":       "Hoş geldin kampanyası ve ilk rezervasyon indirimi gönderin.",
    "At Risk":             "Geri kazanım e-postası: 'Sizi özledik' kampanyası başlatın.",
    "Hibernating":         "Yüksek indirimli flash kampanya ile yeniden aktif edin.",
    "Low Value":           "Düşük maliyetli içerik pazarlaması ile farkındalık artırın.",
}

SEGMENT_ORDER = [
    "Champions", "Loyal Customers", "Potential Loyalists",
    "New Customers", "At Risk", "Hibernating", "Low Value",
]

# ─── Tablo kurulumu ───────────────────────────────────────────────────────────

def ensure_tables() -> None:
    """rfm_scores tablosunu (yoksa) oluşturur."""
    Base.metadata.create_all(bind=engine)


# ─── Ham veri ─────────────────────────────────────────────────────────────────

def _load_events() -> pd.DataFrame:
    try:
        with get_db() as db:
            rows = (
                db.query(
                    UserEvent.user_id,
                    UserEvent.event_type,
                    UserEvent.event_date,
                )
                .filter(UserEvent.user_id.isnot(None))
                .all()
            )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([r._asdict() for r in rows])
        df["event_date"] = pd.to_datetime(df["event_date"])
        return df
    except Exception as exc:
        logger.error("User events yüklenemedi: %s", exc)
        return pd.DataFrame()


# ─── Skorlama yardımcısı ──────────────────────────────────────────────────────

def _quantile_score(series: pd.Series, ascending: bool = True, bins: int = 5) -> pd.Series:
    """Seriyi 1-5 arası skor bandına dönüştürür (quantile-based)."""
    if series.nunique() < 2:
        return pd.Series([3] * len(series), index=series.index, dtype=int)
    labels = list(range(1, bins + 1)) if ascending else list(range(bins, 0, -1))
    try:
        return pd.qcut(series, q=bins, labels=labels, duplicates="drop").astype(int)
    except Exception:
        return pd.Series([3] * len(series), index=series.index, dtype=int)


# ─── Ana hesaplama fonksiyonları ──────────────────────────────────────────────

def calculate_rfm_scores() -> pd.DataFrame:
    """
    Tüm kullanıcılar için RFM değerlerini hesaplar.

    Döner: user_id | recency_days | frequency | monetary | r_score | f_score | m_score | rfm_segment
    """
    df = _load_events()
    if df.empty:
        return pd.DataFrame()

    today = pd.Timestamp.now().normalize()

    # Recency: son yüksek değerli event'ten bu yana gün; yoksa son herhangi event
    high_df = df[df["event_type"].isin(HIGH_VALUE_EVENTS)]
    last_high = (
        high_df.groupby("user_id")["event_date"].max()
        .reset_index()
        .rename(columns={"event_date": "last_high"})
    )
    last_any = (
        df.groupby("user_id")["event_date"].max()
        .reset_index()
        .rename(columns={"event_date": "last_any"})
    )
    recency_df = last_any.merge(last_high, on="user_id", how="left")
    recency_df["last_event"] = recency_df["last_high"].fillna(recency_df["last_any"])
    recency_df["recency_days"] = (today - recency_df["last_event"]).dt.days.clip(lower=0)

    # Frequency: toplam event sayısı
    freq_df = df.groupby("user_id").size().reset_index(name="frequency")

    # Monetary: proxy değer toplamı
    df["m_value"] = df["event_type"].map(MONETARY_WEIGHTS).fillna(0)
    monetary_df = df.groupby("user_id")["m_value"].sum().reset_index(name="monetary")

    rfm = (
        recency_df[["user_id", "recency_days"]]
        .merge(freq_df, on="user_id")
        .merge(monetary_df, on="user_id")
    )

    # R: az gün = yüksek skor → ascending=False (küçük değer → yüksek skor)
    rfm["r_score"] = _quantile_score(rfm["recency_days"], ascending=False)
    rfm["f_score"] = _quantile_score(rfm["frequency"],    ascending=True)
    rfm["m_score"] = _quantile_score(rfm["monetary"],     ascending=True)

    rfm["rfm_segment"] = rfm.apply(
        lambda row: assign_rfm_segment(int(row["r_score"]), int(row["f_score"]), int(row["m_score"])),
        axis=1,
    )

    return rfm[["user_id", "recency_days", "frequency", "monetary",
                "r_score", "f_score", "m_score", "rfm_segment"]]


def assign_rfm_segment(r: int, f: int, m: int) -> str:
    """R, F, M skorlarına (1-5) göre segment atar."""
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r >= 3 and f >= 3:
        return "Loyal Customers"
    if r >= 3 and f >= 2:
        return "Potential Loyalists"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2 and m >= 2:
        return "Hibernating"
    return "Low Value"


def save_rfm_scores(rfm_df: pd.DataFrame) -> int:
    """
    Hesaplanan RFM skorlarını rfm_scores tablosuna kaydeder.
    Mevcut kayıtlar silinerek yenileriyle değiştirilir.

    Döner: kaydedilen kayıt sayısı
    """
    if rfm_df.empty:
        return 0

    calculated_at = datetime.utcnow()
    try:
        with get_db() as db:
            db.query(RFMScore).delete()
            db.bulk_save_objects([
                RFMScore(
                    user_id=int(row.user_id),
                    calculated_at=calculated_at,
                    recency_days=int(row.recency_days),
                    frequency=int(row.frequency),
                    monetary=float(row.monetary),
                    r_score=int(row.r_score),
                    f_score=int(row.f_score),
                    m_score=int(row.m_score),
                    rfm_segment=row.rfm_segment,
                )
                for row in rfm_df.itertuples()
            ])
            db.commit()
            return len(rfm_df)
    except Exception as exc:
        logger.error("RFM skorları kaydedilemedi: %s", exc)
        return 0


# ─── Özet ve tablo fonksiyonları ──────────────────────────────────────────────

def get_segment_summary() -> pd.DataFrame:
    """
    rfm_scores tablosundan segment bazlı özet istatistikler ve kampanya önerileri döndürür.

    Döner: Segment | Kullanıcı Sayısı | Ort. Recency (Gün) | Ort. Frequency | Ort. Monetary | Kampanya Önerisi
    """
    try:
        with get_db() as db:
            rows = db.query(RFMScore).all()
        if not rows:
            return pd.DataFrame()

        raw = pd.DataFrame([{
            "rfm_segment":  r.rfm_segment,
            "recency_days": r.recency_days,
            "frequency":    r.frequency,
            "monetary":     r.monetary,
        } for r in rows])

        summary = (
            raw.groupby("rfm_segment")
            .agg(
                count=("rfm_segment", "count"),
                avg_recency=("recency_days", "mean"),
                avg_frequency=("frequency", "mean"),
                avg_monetary=("monetary", "mean"),
            )
            .reset_index()
        )
        summary["avg_recency"]   = summary["avg_recency"].round(0).astype(int)
        summary["avg_frequency"] = summary["avg_frequency"].round(1)
        summary["avg_monetary"]  = summary["avg_monetary"].round(0).astype(int)
        summary["Kampanya Önerisi"] = summary["rfm_segment"].map(SEGMENT_CAMPAIGNS)

        summary = summary.rename(columns={
            "rfm_segment":   "Segment",
            "count":         "Kullanıcı Sayısı",
            "avg_recency":   "Ort. Recency (Gün)",
            "avg_frequency": "Ort. Frequency",
            "avg_monetary":  "Ort. Monetary",
        })

        order_map = {s: i for i, s in enumerate(SEGMENT_ORDER)}
        summary["_order"] = summary["Segment"].map(lambda s: order_map.get(s, 99))
        return summary.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)

    except Exception as exc:
        logger.error("Segment özeti yüklenemedi: %s", exc)
        return pd.DataFrame()


def get_rfm_table() -> pd.DataFrame:
    """
    rfm_scores tablosunu kullanıcı bilgileriyle birlikte döndürür.

    Döner: Kullanıcı ID | Profil | Şehir | Recency (Gün) | Frequency | Monetary | R | F | M | Segment
    """
    try:
        with get_db() as db:
            rows = (
                db.query(
                    RFMScore.user_id,
                    RFMScore.recency_days,
                    RFMScore.frequency,
                    RFMScore.monetary,
                    RFMScore.r_score,
                    RFMScore.f_score,
                    RFMScore.m_score,
                    RFMScore.rfm_segment,
                    CRMUser.profile_type,
                    CRMUser.city,
                )
                .join(CRMUser, RFMScore.user_id == CRMUser.id)
                .all()
            )
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([r._asdict() for r in rows])
        df["Profil"]   = df["profile_type"].map(lambda x: PROFILE_TR.get(x, x))
        df["Monetary"] = df["monetary"].round(0).astype(int)

        return df.rename(columns={
            "user_id":      "Kullanıcı ID",
            "city":         "Şehir",
            "recency_days": "Recency (Gün)",
            "frequency":    "Frequency",
            "r_score":      "R",
            "f_score":      "F",
            "m_score":      "M",
            "rfm_segment":  "Segment",
        })[["Kullanıcı ID", "Profil", "Şehir", "Recency (Gün)",
            "Frequency", "Monetary", "R", "F", "M", "Segment"]]

    except Exception as exc:
        logger.error("RFM tablosu yüklenemedi: %s", exc)
        return pd.DataFrame()


def get_last_calculation_time() -> datetime | None:
    """rfm_scores tablosundaki en son hesaplanma zamanını döndürür."""
    try:
        with get_db() as db:
            row = db.query(RFMScore.calculated_at).order_by(RFMScore.calculated_at.desc()).first()
        return row[0] if row else None
    except Exception:
        return None
