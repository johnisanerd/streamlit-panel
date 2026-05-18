"""
Instagram Zenginleştirme Paneli — Sprint 10

Public Instagram verilerini otele bağlar; caption analizinden
otel özellikleri çıkarır ve hotels tablosuna uygular.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.enrichment.instagram_enrichment_service import (
    apply_features_to_hotel,
    ensure_tables,
    get_aggregate_features,
    get_hotel_instagram_url,
    get_hotel_posts,
    save_instagram_posts,
)
from src.integrations.apify_instagram_client import (
    _actor_id,
    is_configured,
    scrape_instagram_posts,
)
from src.crm.models import Hotel
from src.database.db import get_db

st.set_page_config(
    page_title="Instagram Zenginleştirme — SuggesMe",
    page_icon="📸",
    layout="wide",
)

ensure_tables()

# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def _load_hotels() -> list[dict]:
    if "ig_hotel_index" not in st.session_state:
        try:
            with get_db() as db:
                hotels = (
                    db.query(Hotel.id, Hotel.name, Hotel.city, Hotel.instagram_url)
                    .filter(Hotel.is_active == True)
                    .order_by(Hotel.name)
                    .all()
                )
                st.session_state["ig_hotel_index"] = [
                    {"id": h.id, "name": h.name, "city": h.city,
                     "instagram_url": h.instagram_url or ""}
                    for h in hotels
                ]
        except Exception as exc:
            st.error(f"Otel listesi yüklenemedi: {exc}")
            st.session_state["ig_hotel_index"] = []
    return st.session_state["ig_hotel_index"]


# ─── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("📸 Instagram Zenginleştirme")

if is_configured():
    st.sidebar.success(f"Apify bağlı · Actor: `{_actor_id()}`")
else:
    st.sidebar.warning("Apify token tanımlı değil — **Demo Mod**")
    st.sidebar.caption("Gerçek scraping yapılmaz; demo Instagram postları gösterilir.")

st.sidebar.divider()

hotels = _load_hotels()
if not hotels:
    st.sidebar.error("Aktif otel bulunamadı.")
    st.stop()

hotel_options = {h["id"]: f"{h['name']} ({h['city']})" for h in hotels}
selected_hotel_id = st.sidebar.selectbox(
    "Otel seçin",
    options=list(hotel_options.keys()),
    format_func=lambda hid: hotel_options[hid],
    key="ig_hotel_id",
)
selected_hotel = next(h for h in hotels if h["id"] == selected_hotel_id)

st.sidebar.divider()
st.sidebar.page_link("streamlit_app.py",            label="← Ana Sayfa",     icon="🏠")
st.sidebar.page_link("pages/7_Business_Onboarding.py", label="İşletme Onboarding", icon="🏢")
st.sidebar.page_link("pages/4_Business_Panel.py",   label="İşletme Paneli",  icon="📊")

# ─── Başlık ───────────────────────────────────────────────────────────────────

st.title("📸 Instagram Zenginleştirme")
st.caption(
    "Public Instagram postlarından otel özelliklerini otomatik çıkarın "
    "ve hotels tablosuna uygulayın. Sadece public veriler kullanılır."
)

tab_scrape, tab_saved = st.tabs(["🔍 Veri Çek", "💾 Kaydedilen Veriler"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Veri çekme
# ══════════════════════════════════════════════════════════════════════════════
with tab_scrape:
    st.subheader(f"Instagram Scraping — {selected_hotel['name']}")

    # Instagram URL — otelde kayıtlıysa pre-fill
    stored_url = selected_hotel.get("instagram_url") or ""
    instagram_url = st.text_input(
        "Instagram URL (profil veya gönderi)",
        value=stored_url,
        placeholder="https://www.instagram.com/username/",
        help="Public profil URL'si (örn: instagram.com/hotelname/) veya belirli bir post URL'si girin.",
    )

    col_limit, col_btn = st.columns([2, 3])
    max_posts = col_limit.slider("Maksimum post sayısı", 1, 20, 10)

    scrape_btn = col_btn.button(
        "📥 Veri Çek",
        type="primary",
        use_container_width=True,
        disabled=not instagram_url.strip(),
    )

    if scrape_btn:
        url = instagram_url.strip()
        if not url.startswith("https://"):
            st.error("Geçerli bir Instagram URL'si girin (https:// ile başlamalı).")
        else:
            with st.spinner("Public Instagram verisi çekiliyor…"):
                try:
                    posts = scrape_instagram_posts(url, max_posts=max_posts)
                except ValueError as exc:
                    st.error(str(exc))
                    posts = []

            if posts:
                st.session_state["ig_scraped_posts"] = posts
                st.session_state["ig_scraped_url"]   = url
                st.success(f"{len(posts)} post başarıyla çekildi.")
            else:
                st.warning("Post bulunamadı. URL'yi veya hesap erişimini kontrol edin.")

    # Çekilen postlar
    if "ig_scraped_posts" in st.session_state:
        scraped = st.session_state["ig_scraped_posts"]
        scraped_url = st.session_state.get("ig_scraped_url", "")

        st.divider()
        st.subheader(f"Önizleme — {len(scraped)} Post")

        all_features: set[str] = set()
        for post in scraped:
            from src.enrichment.instagram_enrichment_service import infer_features
            feats = infer_features(post.get("caption", ""))
            all_features.update(feats)

            with st.expander(
                f"❤️ {post['likes_count']}  💬 {post['comments_count']}  "
                f"{'🏷️ ' + ', '.join(feats) if feats else ''}  "
                f"— {str(post.get('timestamp', ''))[:10]}"
            ):
                st.markdown(post.get("caption") or "_Caption yok_")
                if post.get("comments"):
                    st.markdown("**Yorumlar:**")
                    for c in post["comments"][:5]:
                        st.caption(f"@{c.get('username', '?')}: {c.get('comment_text', '')}")
                st.markdown(f"[Gönderiyi Aç]({post['post_url']})")

        if all_features:
            st.info(f"**Çıkarılan Özellikler:** {', '.join(sorted(all_features))}")

        col_save, col_clear = st.columns([3, 1])
        with col_save:
            if st.button("💾 Verileri Kaydet", type="primary", use_container_width=True):
                try:
                    saved_count = save_instagram_posts(
                        hotel_id=selected_hotel_id,
                        instagram_url=scraped_url,
                        posts=scraped,
                    )
                    st.success(f"{saved_count} yeni post kaydedildi.")
                    # Önbellekleri sıfırla
                    for k in ["ig_scraped_posts", "ig_scraped_url",
                              f"ig_posts_{selected_hotel_id}", f"ig_feats_{selected_hotel_id}"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Kayıt hatası: {exc}")

        with col_clear:
            if st.button("🗑️ Temizle", use_container_width=True):
                st.session_state.pop("ig_scraped_posts", None)
                st.session_state.pop("ig_scraped_url", None)
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Kaydedilen veriler
# ══════════════════════════════════════════════════════════════════════════════
with tab_saved:
    st.subheader(f"Kaydedilen Veriler — {selected_hotel['name']}")

    cache_posts_key = f"ig_posts_{selected_hotel_id}"
    cache_feats_key = f"ig_feats_{selected_hotel_id}"

    if cache_posts_key not in st.session_state:
        st.session_state[cache_posts_key] = get_hotel_posts(selected_hotel_id)
    if cache_feats_key not in st.session_state:
        st.session_state[cache_feats_key] = get_aggregate_features(selected_hotel_id)

    saved_posts    = st.session_state[cache_posts_key]
    agg_features   = st.session_state[cache_feats_key]

    if not saved_posts:
        st.info(
            "Bu otel için henüz kayıtlı Instagram verisi yok. "
            '"Veri Çek" sekmesinden başlayın.'
        )
    else:
        # KPI satırı
        total_likes    = sum(p["likes_count"] for p in saved_posts)
        total_comments = sum(p["comments_count"] for p in saved_posts)
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Post",     len(saved_posts))
        col2.metric("Toplam Beğeni",   f"{total_likes:,}")
        col3.metric("Toplam Yorum",    f"{total_comments:,}")

        # Çıkarılan özellikler + otele uygula
        st.divider()
        st.subheader("Çıkarılan Otel Özellikleri")
        if agg_features:
            st.markdown("Postlardan tespit edilen özellikler:")
            st.write("  ·  ".join(f"**{f}**" for f in agg_features))

            if st.button("✅ Özellikleri Otele Uygula (amenities güncelle)", type="primary"):
                ok = apply_features_to_hotel(selected_hotel_id, agg_features)
                if ok:
                    st.success(
                        f"{len(agg_features)} özellik `hotels.amenities` alanına eklendi."
                    )
                    st.session_state.pop("ig_hotel_index", None)  # otel cache temizle
                else:
                    st.error("Özellikler uygulanamadı.")
        else:
            st.info("Postlardan henüz bir özellik çıkarılamadı.")

        # Post listesi
        st.divider()
        st.subheader("Post Listesi")
        df = pd.DataFrame([{
            "Post URL":      p["post_url"],
            "Tarih":         str(p["timestamp"])[:10] if p["timestamp"] else "—",
            "Beğeni":        p["likes_count"],
            "Yorum":         p["comments_count"],
            "Özellikler":    ", ".join(p["inferred_features"]) if p["inferred_features"] else "—",
            "Caption":       (p["caption"] or "")[:80] + ("…" if len(p["caption"] or "") > 80 else ""),
        } for p in saved_posts])

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Post URL": st.column_config.LinkColumn("Post URL"),
                "Beğeni":   st.column_config.NumberColumn("❤️", format="%d"),
                "Yorum":    st.column_config.NumberColumn("💬", format="%d"),
            },
        )

        if st.button("🔄 Yenile"):
            st.session_state.pop(cache_posts_key, None)
            st.session_state.pop(cache_feats_key, None)
            st.rerun()
