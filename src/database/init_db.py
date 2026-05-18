"""
Veritabanını sıfırdan oluşturur.
Tüm tabloları yaratır ve isteğe bağlı olarak örnek veri ekler.

Kullanım:
    python src/database/init_db.py
    python src/database/init_db.py --seed   # örnek veri ile
"""

import argparse
import sys
from pathlib import Path

# Proje kökünü Python path'ine ekle (doğrudan çalıştırılırken gerekli)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.database.db import Base, engine, get_db
from src.database.models import Interaction, Item, User
import src.crm.models  # noqa: F401 — Hotel, CRMUser, UserEvent tablolarını Base'e kaydeder
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_tables() -> None:
    """Tüm tabloları oluşturur (varsa atlar)."""
    logger.info("Tablolar oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tablolar hazır: %s", list(Base.metadata.tables.keys()))


def seed_data() -> None:
    """Geliştirme ortamı için örnek veri ekler."""
    logger.info("Örnek veri ekleniyor...")

    sample_users = [
        User(username="alice", email="alice@example.com"),
        User(username="bob", email="bob@example.com"),
        User(username="carol", email="carol@example.com"),
    ]

    sample_items = [
        Item(title="Python ile Veri Bilimi", category="kitap", tags='["python","veri bilimi","pandas"]'),
        Item(title="Derin Öğrenme Temelleri", category="kurs", tags='["yapay zeka","neural network"]'),
        Item(title="Clean Code", category="kitap", tags='["yazılım","best practices"]'),
        Item(title="FastAPI ile REST API", category="kurs", tags='["python","api","web"]'),
        Item(title="SQL ve Veritabanı Tasarımı", category="kurs", tags='["sql","veritabani"]'),
    ]

    with get_db() as db:
        # Kullanıcılar zaten varsa tekrar ekleme
        if db.query(User).count() == 0:
            db.add_all(sample_users)
            db.flush()

            db.add_all(sample_items)
            db.flush()

            interactions = [
                Interaction(user_id=sample_users[0].id, item_id=sample_items[0].id, interaction_type="like", rating=5.0),
                Interaction(user_id=sample_users[0].id, item_id=sample_items[2].id, interaction_type="view"),
                Interaction(user_id=sample_users[1].id, item_id=sample_items[1].id, interaction_type="rate", rating=4.0),
                Interaction(user_id=sample_users[1].id, item_id=sample_items[3].id, interaction_type="like", rating=4.5),
                Interaction(user_id=sample_users[2].id, item_id=sample_items[4].id, interaction_type="view"),
            ]
            db.add_all(interactions)
            logger.info("Örnek veri eklendi: %d kullanıcı, %d içerik, %d etkileşim", len(sample_users), len(sample_items), len(interactions))
        else:
            logger.info("Veri zaten mevcut, seed atlandı.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggesme veritabanını başlatır")
    parser.add_argument("--seed", action="store_true", help="Örnek veri ekle")
    args = parser.parse_args()

    # data/ dizinini oluştur (SQLite dosyası burada oluşacak)
    from src.utils.config import config
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    create_tables()

    if args.seed:
        seed_data()

    logger.info("Veritabanı hazır.")


if __name__ == "__main__":
    main()
