"""
Otel kümeleme sistemi — Sprint 11

KMeans ile otelleri özellik vektörlerine göre gruplandırır.
Model basit ve açıklanabilir: 9 boyutlu vektör, sklearn KMeans.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src.recommendation.recommender import PROFILE_TAGS, load_hotels_df
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Küme etiketleme ──────────────────────────────────────────────────────────

# Özellik vektörü boyut sırası: price_level, rating, stars, [6 profil etiketi]
_FEATURE_COLS = ["price_level", "rating", "stars"] + [f"tag_{t}" for t in PROFILE_TAGS]

_PRICE_LABELS = {
    (0.00, 0.25): "Ekonomik",
    (0.25, 0.60): "Orta Segment",
    (0.60, 1.01): "Premium",
}

_TAG_LABELS = {
    "tag_luxury_traveler":   "Lüks",
    "tag_family_vacation":   "Aile Dostu",
    "tag_budget_traveler":   "Ekonomik",
    "tag_honeymoon":         "Romantik",
    "tag_business_traveler": "İş Seyahati",
    "tag_wellness_spa":      "Wellness & Spa",
}

PREDEFINED_CLUSTER_NAMES = [
    "Lüks Sahil & Premium",
    "Ekonomik Şehir Otelleri",
    "Aile Dostu Tatil",
    "Wellness & Spa Kaçamak",
    "Romantik Butik Otel",
]


def _name_cluster(centroid: np.ndarray) -> str:
    """Küme merkezi vektörüne bakarak okunabilir küme adı atar."""
    price = centroid[0]

    # Fiyat etiketi
    price_label = "Orta Segment"
    for (lo, hi), lbl in _PRICE_LABELS.items():
        if lo <= price < hi:
            price_label = lbl
            break

    # Dominant profil etiketi (index 3-8)
    tag_vals = centroid[3:]
    if tag_vals.max() > 0.1:
        dominant_idx = int(np.argmax(tag_vals))
        tag_key = list(_TAG_LABELS.keys())[dominant_idx]
        tag_label = _TAG_LABELS[tag_key]
    else:
        tag_label = "Genel"

    return f"{tag_label} · {price_label}"


# ─── Ana kümeleme fonksiyonu ──────────────────────────────────────────────────

def cluster_hotels(n_clusters: int = 5, random_state: int = 42) -> pd.DataFrame:
    """
    Aktif otelleri KMeans ile kümeler.

    Döner: hotel_id, name, city, price_level, rating, stars,
           profile_tags, cluster_id, cluster_name, feature vektör sütunları
    """
    df = load_hotels_df()
    if df.empty:
        return pd.DataFrame()

    n_clusters = min(n_clusters, len(df))
    if n_clusters < 2:
        df["cluster_id"]   = 0
        df["cluster_name"] = "Tek Grup"
        return df

    # Özellik matrisi
    X = np.vstack(df["feature_vec"].values)

    try:
        km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        centroids = km.cluster_centers_
    except Exception as exc:
        logger.error("KMeans hatası: %s", exc)
        df["cluster_id"]   = 0
        df["cluster_name"] = "Kümeleme Hatası"
        return df

    df = df.copy()
    df["cluster_id"]   = labels
    df["cluster_name"] = [_name_cluster(centroids[c]) for c in labels]

    return df[["hotel_id", "name", "city", "district", "price_level", "rating", "stars",
               "review_count", "profile_tags", "cluster_id", "cluster_name"]]


def get_cluster_summary(cluster_df: pd.DataFrame) -> pd.DataFrame:
    """
    Küme bazlı özet istatistikler.

    Döner: cluster_id, cluster_name, otel_sayisi, ort_rating, ort_fiyat_seviyesi, profil_etiketleri
    """
    if cluster_df.empty:
        return pd.DataFrame()

    price_decode = {"budget": 0, "mid": 1, "luxury": 2}

    summary_rows = []
    for (cid, cname), grp in cluster_df.groupby(["cluster_id", "cluster_name"]):
        # Baskın profil etiketleri (en sık geçenler)
        all_tags: list[str] = []
        for tags in grp["profile_tags"]:
            if isinstance(tags, list):
                all_tags.extend(tags)
        from collections import Counter
        top_tags = [t for t, _ in Counter(all_tags).most_common(3)]

        avg_price = grp["price_level"].map(price_decode).mean()
        price_label = "Ekonomik" if avg_price < 0.8 else ("Orta" if avg_price < 1.5 else "Lüks")

        summary_rows.append({
            "Küme ID":          int(cid),
            "Küme Adı":         cname,
            "Otel Sayısı":      len(grp),
            "Ort. Rating":      round(grp["rating"].mean(), 2),
            "Fiyat Segmenti":   price_label,
            "Baskın Profiller": ", ".join(top_tags) if top_tags else "—",
        })

    return pd.DataFrame(summary_rows).sort_values("Küme ID").reset_index(drop=True)
