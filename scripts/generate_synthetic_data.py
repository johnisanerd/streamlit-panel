"""
Sentetik CRM verisi üretme scripti.

Kullanım:
    python scripts/generate_synthetic_data.py
    python scripts/generate_synthetic_data.py --reset
    python scripts/generate_synthetic_data.py --reset --seed 123
    python scripts/generate_synthetic_data.py --export-csv
    python scripts/generate_synthetic_data.py --hotels 50 --users 1000 --events 10000

Notlar:
    --reset     : Mevcut hotels, crm_users, user_events tablolarını temizleyip yeniden doldurur.
    --export-csv: data/ klasörüne .csv dosyaları da oluşturur.
    --seed      : Aynı seed ile her çalıştırmada aynı veri üretilir.
"""

import argparse
import sys
from pathlib import Path

# Proje kökünü Python path'ine ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.crm.synthetic_data_generator import SyntheticDataGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Yardımcı ────────────────────────────────────────────────────────────────

_COL_W = 28


def _print_summary(summary: dict[str, int]) -> None:
    """Üretim özetini formatlı olarak yazdırır."""
    sep = "=" * ((_COL_W + 8))
    print(f"\n{sep}")
    print("  Sentetik Veri Üretimi Tamamlandı")
    print(sep)
    for key, value in sorted(summary.items()):
        print(f"  {key:<{_COL_W}} {value:>6}")
    print(sep + "\n")


# ─── Ana akış ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suggesme — sentetik CRM verisi üretici",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--reset",      action="store_true",  help="Mevcut CRM verisini sil ve yeniden oluştur")
    parser.add_argument("--seed",       type=int, default=42, help="Rastgelelik tohumu (default: 42)")
    parser.add_argument("--hotels",     type=int, default=30, help="Otel sayısı (default: 30)")
    parser.add_argument("--users",      type=int, default=500,  help="Kullanıcı sayısı (default: 500)")
    parser.add_argument("--events",     type=int, default=5000, help="Event sayısı (default: 5 000)")
    parser.add_argument("--export-csv", action="store_true",  help="Veriyi CSV olarak da dışa aktar")
    args = parser.parse_args()

    # data/ dizinini oluştur
    from src.utils.config import config
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    generator = SyntheticDataGenerator(
        n_hotels=args.hotels,
        n_users=args.users,
        n_events=args.events,
        seed=args.seed,
    )

    if args.reset:
        logger.info("--reset aktif: mevcut CRM verisi temizlenecek.")

    summary = generator.generate(reset=args.reset)
    _print_summary(summary)

    if args.export_csv:
        logger.info("CSV dışa aktarımı başlıyor...")
        generator.export_csv()
        print(f"CSV dosyaları → {config.DATA_DIR}\n")


if __name__ == "__main__":
    main()
