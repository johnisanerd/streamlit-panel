#!/usr/bin/env python3
"""
Apify Google Maps istemcisi CLI test scripti — Sprint 9

Kullanım:
    python scripts/test_apify_maps.py "Sürmeli Hotel Ankara"
    python scripts/test_apify_maps.py "Hilton Istanbul Bosphorus" --max 3
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.integrations.apify_maps_client import (
    _actor_id,
    is_configured,
    masked_token,
    normalize_place,
    search_places,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apify Google Maps arama testi")
    parser.add_argument("query", nargs="*", help="Arama sorgusu (örn: 'Hilton Istanbul')")
    parser.add_argument("--max", type=int, default=5, help="Maksimum sonuç sayısı (varsayılan: 5)")
    args = parser.parse_args()

    query = " ".join(args.query) if args.query else "Hotel Istanbul"

    print("\n── Apify Google Maps Test ─────────────────────────────────────")
    print(f"Token : {masked_token()}")
    print(f"Actor : {_actor_id()}")
    print(f"Mod   : {'Canlı' if is_configured() else 'Demo'}")
    print(f"Sorgu : {query!r}")
    print(f"Limit : {args.max}")
    print("────────────────────────────────────────────────────────────────\n")

    try:
        results = search_places(query, max_results=args.max)
    except ValueError as exc:
        print(f"HATA: {exc}")
        sys.exit(1)

    if not results:
        print("Sonuç bulunamadı.")
        sys.exit(0)

    print(f"{len(results)} sonuç:\n")
    for i, place in enumerate(results, 1):
        rating_str = f"{place['rating']} ⭐" if place.get("rating") else "—"
        print(f"  {i}. {place['name']}")
        print(f"     Kategori : {place.get('category') or '—'}")
        print(f"     Adres    : {place.get('address') or '—'}")
        print(f"     Telefon  : {place.get('phone') or '—'}")
        print(f"     Website  : {place.get('website') or '—'}")
        print(f"     Rating   : {rating_str} ({place.get('review_count', 0)} yorum)")
        print(f"     Konum    : {place.get('latitude')}, {place.get('longitude')}")
        print(f"     Maps URL : {place.get('google_maps_url') or '—'}")
        print()


if __name__ == "__main__":
    main()
