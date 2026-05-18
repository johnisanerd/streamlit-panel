"""
Apify Instagram API istemcisi — Sprint 10

Public Instagram profillerinden gönderi verisi çeker.
Sadece public veriler; login, DM ve private hesap verisi çekilmez.
APIFY_API_TOKEN tanımlı değilse demo modda çalışır.
"""

import json
import urllib.error
import urllib.request
from datetime import datetime

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

_APIFY_BASE = "https://api.apify.com/v2"

# ─── Konfigürasyon ────────────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(config.APIFY_API_TOKEN)


def _actor_id() -> str:
    return config.APIFY_INSTAGRAM_ACTOR_ID or "apify/instagram-scraper"


# ─── Actor I/O — burası değiştirilirse yeterli ────────────────────────────────

def build_actor_input(instagram_url: str, max_posts: int = 10) -> dict:
    """
    Apify Instagram actor giriş parametrelerini oluşturur.
    Actor değişirse sadece bu fonksiyonu güncelleyin.
    Sadece public veri — login gerektiren alanlar kullanılmaz.
    """
    return {
        "directUrls":    [instagram_url],
        "resultsType":   "posts",
        "resultsLimit":  max_posts,
        "addParentData": False,
    }


def normalize_post(raw: dict) -> dict:
    """
    Apify actor çıktısını standart alanlarımıza dönüştürür.
    Actor değişirse sadece bu fonksiyonu güncelleyin.
    """
    raw_comments = raw.get("latestComments") or raw.get("comments") or []
    comments = [
        {
            "username":     c.get("ownerUsername") or c.get("username", ""),
            "comment_text": c.get("text") or c.get("comment", ""),
        }
        for c in raw_comments
        if c.get("text") or c.get("comment")
    ]

    # Timestamp: ISO string → datetime
    ts_raw = raw.get("timestamp") or raw.get("takenAtTimestamp")
    timestamp = None
    if ts_raw:
        try:
            timestamp = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except Exception:
            pass

    return {
        "post_url":       raw.get("url") or raw.get("shortCode", ""),
        "caption":        raw.get("caption") or "",
        "likes_count":    int(raw.get("likesCount") or raw.get("likeCount") or 0),
        "comments_count": int(raw.get("commentsCount") or raw.get("commentCount") or 0),
        "timestamp":      timestamp,
        "comments":       comments,
    }


# ─── Ana scraping fonksiyonu ──────────────────────────────────────────────────

def scrape_instagram_posts(instagram_url: str, max_posts: int = 10) -> list[dict]:
    """
    Public Instagram URL'inden gönderi verisi çeker.

    - Token tanımlı değilse → demo veri (ValueError fırlatmaz)
    - Actor ID hatalıysa → ValueError (kullanıcı dostu mesajla)
    - Private hesap / login gereksinimi → ValueError
    """
    if not is_configured():
        logger.info("APIFY_API_TOKEN tanımlı değil — demo mod.")
        return _demo_posts(instagram_url)

    actor = _actor_id()
    token = config.APIFY_API_TOKEN
    url = (
        f"{_APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items"
        f"?token={token}&timeout=90&memory=512"
    )

    try:
        data = json.dumps(build_actor_input(instagram_url, max_posts), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=150) as resp:
            raw_list = json.loads(resp.read().decode("utf-8"))
            posts = [normalize_post(p) for p in raw_list if p]
            # Geçersiz post_url'leri filtrele
            return [p for p in posts if p.get("post_url")]

    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass

        if exc.code in (401, 403):
            raise ValueError(
                "APIFY_API_TOKEN geçersiz veya bu actor için yetkiniz yok."
            ) from exc
        if exc.code == 404:
            raise ValueError(
                f"Instagram actor bulunamadı: '{actor}'. "
                "APIFY_INSTAGRAM_ACTOR_ID değerini kontrol edin."
            ) from exc
        if "private" in body.lower():
            raise ValueError(
                "Bu hesap private (gizli). Sadece public hesaplar desteklenir."
            ) from exc
        raise ValueError(f"Apify API hatası (HTTP {exc.code}): {body}") from exc

    except urllib.error.URLError as exc:
        raise ValueError(f"Ağ bağlantısı hatası: {exc.reason}") from exc


# ─── Demo veri ────────────────────────────────────────────────────────────────

def _demo_posts(instagram_url: str) -> list[dict]:
    """Token tanımlı değilken gösterilecek statik demo veriler."""
    now = datetime.utcnow()
    return [
        {
            "post_url":       "https://www.instagram.com/p/demo_post_1/",
            "caption":        (
                "Boğaz manzarası eşliğinde kahvaltı keyfi 🌅 "
                "Havuzumuz sabah 7'den itibaren misafirlerimize açık. "
                "#istanbul #hotel #havuz #breakfast #bogazmanzarasi"
            ),
            "likes_count":    1247,
            "comments_count": 38,
            "timestamp":      now.replace(day=max(1, now.day - 2)),
            "comments": [
                {"username": "traveler_az",  "comment_text": "Kahvaltı mükemmeldi!"},
                {"username": "istanbul_fan", "comment_text": "Boğaz manzarası harika 😍"},
            ],
        },
        {
            "post_url":       "https://www.instagram.com/p/demo_post_2/",
            "caption":        (
                "Spa ve wellness merkezimizde huzurlu bir gün 🧘 "
                "Hamam, sauna ve masaj seçeneklerimiz için rezervasyon yapın. "
                "#spa #wellness #hamam #sauna #relaxation"
            ),
            "likes_count":    893,
            "comments_count": 22,
            "timestamp":      now.replace(day=max(1, now.day - 5)),
            "comments": [
                {"username": "wellness_lover", "comment_text": "Spa programı çok güzeldi"},
            ],
        },
        {
            "post_url":       "https://www.instagram.com/p/demo_post_3/",
            "caption":        (
                "Balkon odalarımızda deniz manzarası ve romantik akşam yemeği ✨ "
                "Çiftlere özel balayı paketi için bize ulaşın. "
                "#romantic #honeymoon #seaview #balkon #denizmanzarası"
            ),
            "likes_count":    2104,
            "comments_count": 67,
            "timestamp":      now.replace(day=max(1, now.day - 8)),
            "comments": [
                {"username": "couple_travel", "comment_text": "Balayımızda kaldık, unutulmaz bir deneyimdi!"},
                {"username": "sea_lover",     "comment_text": "Deniz manzarası inanılmaz 🌊"},
            ],
        },
        {
            "post_url":       "https://www.instagram.com/p/demo_post_4/",
            "caption":        (
                "Toplantı ve etkinlik salonlarımız tam donanımlı 💼 "
                "WiFi, projeksiyon ve catering hizmetiyle iş dünyasının tercihiyiz. "
                "#business #toplantı #meeting #wifi #conference"
            ),
            "likes_count":    412,
            "comments_count": 9,
            "timestamp":      now.replace(day=max(1, now.day - 12)),
            "comments": [],
        },
        {
            "post_url":       "https://www.instagram.com/p/demo_post_5/",
            "caption":        (
                "Çocuklarınız için özel aktiviteler ve çocuk kulübümüz hazır 👨‍👩‍👧 "
                "Otopark, plaj erişimi ve aile odalarımızla tam konfor! "
                "#family #kids #çocukkulübü #plaj #otopark"
            ),
            "likes_count":    766,
            "comments_count": 31,
            "timestamp":      now.replace(day=max(1, now.day - 15)),
            "comments": [
                {"username": "family_trips", "comment_text": "Çocuklar çok eğlendi, harika bir otel!"},
            ],
        },
    ]
