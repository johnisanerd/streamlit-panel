"""
n8n webhook istemcisi — Sprint 8

Kampanya payload'larını n8n webhook URL'ine gönderir.
N8N_WEBHOOK_URL yapılandırılmamışsa demo modda çalışır (gerçek HTTP isteği yapılmaz).
"""

import json
import urllib.error
import urllib.request
from datetime import datetime

from src.crm.models import AutomationEvent, Hotel
from src.database.db import Base, engine, get_db
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

CHANNELS: list[str] = ["email", "whatsapp", "instagram"]

CAMPAIGN_TYPES: list[str] = [
    "İndirim Kampanyası",
    "Geri Kazanım",
    "Sadakat Programı",
    "Yeni Sezon Duyurusu",
    "Flash Fırsat",
]

SEGMENT_MESSAGES: dict[str, str] = {
    "Champions": (
        "Sizi değerli müşterimiz olarak tanıyoruz. {hotel_name}'de size özel "
        "VIP ayrıcalıkları ve %15 indirim sunuyoruz."
    ),
    "Loyal Customers": (
        "{hotel_name}'e olan bağlılığınız için teşekkür ederiz. "
        "Sadakat programımıza katılın, erken rezervasyon avantajından yararlanın!"
    ),
    "Potential Loyalists": (
        "{hotel_name}'de unutulmaz bir deneyim için özel teklifimizi kaçırmayın. "
        "Sizi bekliyoruz!"
    ),
    "New Customers": (
        "{hotel_name}'e hoş geldiniz! "
        "İlk rezervasyonunuza özel %10 indirim kazanın."
    ),
    "At Risk": (
        "Sizi özledik! {hotel_name}'de yeniden buluşmak için "
        "size özel geri dönüş teklifimiz hazır."
    ),
    "Hibernating": (
        "{hotel_name}'de yeniden buluşalım. "
        "Sınırlı süreli flash fırsatımızı kaçırmayın!"
    ),
    "Low Value": (
        "{hotel_name}'i keşfedin. "
        "Size özel içerik ve fırsatlarla dolu bir deneyim sizi bekliyor."
    ),
}

# ─── Tablo kurulumu ───────────────────────────────────────────────────────────

def ensure_tables() -> None:
    """automation_events tablosunu (yoksa) oluşturur."""
    Base.metadata.create_all(bind=engine)


# ─── Webhook ──────────────────────────────────────────────────────────────────

def is_webhook_configured() -> bool:
    return bool(config.N8N_WEBHOOK_URL)


def build_payload(
    campaign_name: str,
    hotel_name: str,
    segment: str,
    channel: str,
    campaign_type: str,
    message: str,
    target_user_count: int,
) -> dict:
    return {
        "campaign_name":     campaign_name,
        "hotel_name":        hotel_name,
        "segment":           segment,
        "channel":           channel,
        "campaign_type":     campaign_type,
        "message":           message,
        "target_user_count": target_user_count,
        "created_at":        datetime.utcnow().isoformat(),
    }


def send_webhook(payload: dict) -> dict:
    """
    Payload'ı N8N webhook URL'ine gönderir.
    URL yapılandırılmamışsa demo modda simüle eder.

    Döner: {"mode": "demo"|"live", "status": "simulated"|"sent"|"failed", ...}
    """
    url = config.N8N_WEBHOOK_URL
    if not url:
        logger.info("N8N_WEBHOOK_URL tanımlı değil — demo modda simüle edildi.")
        return {"mode": "demo", "status": "simulated"}

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Webhook gönderildi: %d", resp.status)
            return {"mode": "live", "status": "sent", "status_code": resp.status}
    except urllib.error.HTTPError as exc:
        logger.error("Webhook HTTP hatası %d: %s", exc.code, exc)
        return {"mode": "live", "status": "failed", "status_code": exc.code, "error": str(exc)}
    except Exception as exc:
        logger.error("Webhook gönderilemedi: %s", exc)
        return {"mode": "live", "status": "failed", "error": str(exc)}


# ─── Veritabanı ───────────────────────────────────────────────────────────────

def save_automation_event(
    hotel_id: int | None,
    payload: dict,
    webhook_result: dict,
) -> bool:
    """Gönderilen kampanyayı automation_events tablosuna kaydeder."""
    try:
        with get_db() as db:
            db.add(AutomationEvent(
                hotel_id=hotel_id,
                campaign_name=payload.get("campaign_name", ""),
                segment=payload.get("segment", ""),
                channel=payload.get("channel", ""),
                campaign_type=payload.get("campaign_type", ""),
                message=payload.get("message", ""),
                target_user_count=payload.get("target_user_count", 0),
                webhook_status=webhook_result.get("status", "unknown"),
                payload_json=json.dumps(payload, ensure_ascii=False),
            ))
            db.commit()
        return True
    except Exception as exc:
        logger.error("AutomationEvent kaydedilemedi: %s", exc)
        return False


def get_campaign_history(limit: int = 20) -> list[dict]:
    """Son N kampanya kaydını döndürür."""
    try:
        with get_db() as db:
            rows = (
                db.query(
                    AutomationEvent.id,
                    AutomationEvent.campaign_name,
                    AutomationEvent.segment,
                    AutomationEvent.channel,
                    AutomationEvent.campaign_type,
                    AutomationEvent.target_user_count,
                    AutomationEvent.webhook_status,
                    AutomationEvent.created_at,
                    Hotel.name.label("hotel_name"),
                )
                .outerjoin(Hotel, AutomationEvent.hotel_id == Hotel.id)
                .order_by(AutomationEvent.created_at.desc())
                .limit(limit)
                .all()
            )
        return [r._asdict() for r in rows]
    except Exception as exc:
        logger.error("Kampanya geçmişi yüklenemedi: %s", exc)
        return []
