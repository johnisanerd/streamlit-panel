#!/usr/bin/env python3
"""
Apify Instagram istemcisi CLI test scripti — Sprint 10

Sadece public Instagram verisi çekilir. Private hesaplar desteklenmez.

Kullanım:
    python scripts/test_apify_instagram.py https://www.instagram.com/username/
    python scripts/test_apify_instagram.py https://www.instagram.com/username/ --max 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.integrations.apify_instagram_client import (
    _actor_id,
    is_configured,
    scrape_instagram_posts,
)
from src.integrations.apify_maps_client import masked_token
from src.enrichment.instagram_enrichment_service import infer_features


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apify Instagram scraper testi (sadece public veriler)"
    )
    parser.add_argument("url", help="Public Instagram profil veya post URL'si")
    parser.add_argument("--max", type=int, default=5, help="Maksimum post sayısı (varsayılan: 5)")
    args = parser.parse_args()

    print("\n── Apify Instagram Test ────────────────────────────────────────")
    print(f"Token  : {masked_token()}")
    print(f"Actor  : {_actor_id()}")
    print(f"Mod    : {'Canlı' if is_configured() else 'Demo'}")
    print(f"URL    : {args.url}")
    print(f"Limit  : {args.max}")
    print("────────────────────────────────────────────────────────────────\n")

    try:
        posts = scrape_instagram_posts(args.url, max_posts=args.max)
    except ValueError as exc:
        print(f"HATA: {exc}")
        sys.exit(1)

    if not posts:
        print("Post bulunamadı.")
        sys.exit(0)

    print(f"{len(posts)} post:\n")
    for i, post in enumerate(posts, 1):
        features = infer_features(post.get("caption", ""))
        ts = str(post.get("timestamp", ""))[:10]
        print(f"  {i}. {post['post_url']}")
        print(f"     Tarih     : {ts or '—'}")
        print(f"     Beğeni    : {post['likes_count']}")
        print(f"     Yorum     : {post['comments_count']}")
        print(f"     Özellikler: {', '.join(features) or '—'}")
        caption = (post.get("caption") or "")[:100]
        if caption:
            print(f"     Caption   : {caption}{'…' if len(post.get('caption',''))>100 else ''}")
        if post.get("comments"):
            print(f"     İlk yorum : @{post['comments'][0].get('username','?')}: "
                  f"{post['comments'][0].get('comment_text','')[:60]}")
        print()


if __name__ == "__main__":
    main()
