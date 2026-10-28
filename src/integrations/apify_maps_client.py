"""
Apify Google Maps API istemcisi — Sprint 9

İşletme onboarding ve otel discovery için Google Maps yer arama.
APIFY_API_TOKEN tanımlı değilse demo modda sabit veri döndürür.
"""

import json
import urllib.error
import urllib.request

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

_APIFY_BASE  = "https://api.apify.com/v2"
_DEFAULT_ACTOR = "johnvc~google-maps-places-api"

# ─── Konfigürasyon ────────────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(config.APIFY_API_TOKEN)


def masked_token() -> str:
    """Token'ı ekranda güvenli gösterir — ilk/son 4 karakter görünür."""
    token = config.APIFY_API_TOKEN
    if not token:
        return "(tanımlı değil)"
    if len(token) <= 8:
        return "***"
    return token[:4] + "***" + token[-4:]


def _actor_id() -> str:
    return config.APIFY_GOOGLE_MAPS_ACTOR_ID or _DEFAULT_ACTOR


# ─── Actor I/O — burası değiştirilirse yeterli ────────────────────────────────

def build_actor_input(query: str, max_results: int = 5) -> dict:
    """
    Apify actor giriş parametrelerini oluşturur.
    Actor değişirse sadece bu fonksiyonu güncelleyin.
    """
    return {
        "searchTerms":               [query],
        "maxResultsPerSearch":       max(max_results, 20),  # actor en az 20 sonuç ister
        "language":                  "tr",
    }


def normalize_place(raw: dict) -> dict:
    """
    Apify actor çıktısını standart alanlarımıza dönüştürür.
    Actor değişirse sadece bu fonksiyonu güncelleyin.
    """
    loc = raw.get("location") or {}
    cid = raw.get("cid")
    maps_url = f"https://maps.google.com/?cid={cid}" if cid else ""
    return {
        "name":            raw.get("title") or raw.get("name", ""),
        "address":         raw.get("address", ""),
        "phone":           raw.get("phone") or raw.get("phoneNumber", ""),
        "website":         raw.get("website", ""),
        "google_maps_url": raw.get("url") or raw.get("googleMapsUrl") or maps_url,
        "rating":          raw.get("totalScore") or raw.get("rating"),
        "review_count":    int(raw.get("reviewsCount") or raw.get("reviewCount") or raw.get("ratingCount") or 0),
        "latitude":        loc.get("lat") or raw.get("lat") or raw.get("latitude"),
        "longitude":       loc.get("lng") or raw.get("lng") or raw.get("longitude"),
        "category":        raw.get("categoryName") or raw.get("category") or raw.get("type", ""),
    }


# ─── Ana arama fonksiyonu ─────────────────────────────────────────────────────

def search_places(query: str, max_results: int = 5) -> list[dict]:
    """
    Google Maps'te yer arar ve normalize edilmiş sonuçlar döndürür.

    - Token tanımlı değilse → demo veri (ValueError fırlatmaz)
    - Actor ID hatalıysa → ValueError (kullanıcı dostu mesajla)
    - Ağ hatası → ValueError
    """
    if not is_configured():
        logger.info("APIFY_API_TOKEN tanımlı değil — demo mod.")
        return _demo_results(query)

    actor = _actor_id()
    token = config.APIFY_API_TOKEN
    url = (
        f"{_APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items"
        f"?token={token}&timeout=60&memory=512"
    )

    try:
        data = json.dumps(build_actor_input(query, max_results), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw_list = json.loads(resp.read().decode("utf-8"))
            raw_list = [p for p in raw_list if p and not p.get("error_message")]
            return [normalize_place(p) for p in raw_list][:max_results]

    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass

        if exc.code in (401, 403):
            raise ValueError(
                "APIFY_API_TOKEN geçersiz veya bu actor için yetkiniz yok. "
                "Apify hesabınızı kontrol edin."
            ) from exc
        if exc.code == 404:
            raise ValueError(
                f"Actor bulunamadı: '{actor}'. "
                "APIFY_GOOGLE_MAPS_ACTOR_ID değerini kontrol edin "
                f"(varsayılan: '{_DEFAULT_ACTOR}')."
            ) from exc
        raise ValueError(f"Apify API hatası (HTTP {exc.code}): {body}") from exc

    except urllib.error.URLError as exc:
        raise ValueError(f"Ağ bağlantısı hatası: {exc.reason}") from exc


# ─── Demo veri ────────────────────────────────────────────────────────────────

def _demo_results(query: str) -> list[dict]:
    """APIFY_API_TOKEN tanımlı olmadığında gösterilecek statik demo veriler."""
    return [
        {
            "name":            "Çırağan Palace Kempinski Istanbul",
            "address":         "Çırağan Cd. No:32, 34349 Beşiktaş/İstanbul",
            "phone":           "+90 212 326 46 46",
            "website":         "https://www.kempinski.com/istanbul",
            "google_maps_url": "https://maps.google.com/?cid=demo1",
            "rating":          4.7,
            "review_count":    3842,
            "latitude":        41.0495,
            "longitude":       29.0287,
            "category":        "5 Yıldızlı Otel",
        },
        {
            "name":            "The Ritz-Carlton, Istanbul",
            "address":         "Süzer Plaza, Elmadağ, 34367 Şişli/İstanbul",
            "phone":           "+90 212 334 44 44",
            "website":         "https://www.ritzcarlton.com/istanbul",
            "google_maps_url": "https://maps.google.com/?cid=demo2",
            "rating":          4.6,
            "review_count":    2157,
            "latitude":        41.0452,
            "longitude":       28.9987,
            "category":        "5 Yıldızlı Otel",
        },
        {
            "name":            "Hilton Istanbul Bosphorus",
            "address":         "Cumhuriyet Cd., 34367 Elmadağ/İstanbul",
            "phone":           "+90 212 315 60 00",
            "website":         "https://www.hilton.com/istanbul-bosphorus",
            "google_maps_url": "https://maps.google.com/?cid=demo3",
            "rating":          4.3,
            "review_count":    1893,
            "latitude":        41.0469,
            "longitude":       28.9955,
            "category":        "5 Yıldızlı Otel",
        },
        {
            "name":            "Hotel Sultania",
            "address":         "Piyer Loti Cd. No:12, 34490 Fatih/İstanbul",
            "phone":           "+90 212 516 33 23",
            "website":         "https://www.hotelsultania.com",
            "google_maps_url": "https://maps.google.com/?cid=demo4",
            "rating":          4.5,
            "review_count":    612,
            "latitude":        41.0082,
            "longitude":       28.9784,
            "category":        "Butik Otel",
        },
        {
            "name":            "Wyndham Grand Istanbul Kalamış Marina",
            "address":         "Kalamış Marina, 34726 Fenerbahçe/İstanbul",
            "phone":           "+90 216 542 44 44",
            "website":         "https://www.wyndhamhotels.com",
            "google_maps_url": "https://maps.google.com/?cid=demo5",
            "rating":          4.2,
            "review_count":    987,
            "latitude":        40.9725,
            "longitude":       29.0573,
            "category":        "5 Yıldızlı Otel",
        },
    ]
