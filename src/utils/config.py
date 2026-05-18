"""
Uygulama yapılandırmasını yöneten modül.
.env dosyasından değerleri okur ve tip-güvenli erişim sağlar.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizinini bul ve .env dosyasını yükle
_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_ROOT / ".env")


class Config:
    """Uygulama yapılandırma değerlerine erişim sağlar."""

    # Uygulama
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    APP_NAME: str = os.getenv("APP_NAME", "Suggesme")

    # Veritabanı
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_ROOT / 'data' / 'suggesme.db'}")

    # Loglama
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(_ROOT / "logs" / "suggesme.log"))

    # Otomasyon
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")

    # Apify entegrasyonu
    APIFY_API_TOKEN:              str = os.getenv("APIFY_API_TOKEN", "")
    APIFY_GOOGLE_MAPS_ACTOR_ID:   str = os.getenv("APIFY_GOOGLE_MAPS_ACTOR_ID", "")
    APIFY_INSTAGRAM_ACTOR_ID:     str = os.getenv("APIFY_INSTAGRAM_ACTOR_ID", "apify/instagram-scraper")

    # Proje kök dizini
    ROOT_DIR: Path = _ROOT
    DATA_DIR: Path = _ROOT / "data"

    @classmethod
    def is_development(cls) -> bool:
        return cls.APP_ENV == "development"

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"


config = Config()
