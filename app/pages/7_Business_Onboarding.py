"""
İşletme Onboarding Paneli — Sprint 9

İşletme sahiplerinin Apify Google Maps üzerinden kendi otellerini
bulup sisteme kaydetmelerini sağlar.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.business.business_onboarding_service import (
    create_hotel_from_place,
    ensure_tables,
    find_existing_hotel,
    get_registered_businesses,
    register_business_account,
)
from src.integrations.apify_maps_client import (
    is_configured,
    masked_token,
    search_places,
)

st.set_page_config(
    page_title="İşletme Onboarding — SuggesMe",
    page_icon="🏢",
    layout="wide",
)

ensure_tables()

# ─── Session state başlatma ───────────────────────────────────────────────────

def _reset_flow() -> None:
    for key in ["ob_step", "ob_results", "ob_selected", "ob_query_city", "ob_query_district"]:
        st.session_state.pop(key, None)


if "ob_step" not in st.session_state:
    st.session_state["ob_step"] = 1

# ─── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("🏢 İşletme Onboarding")

if is_configured():
    st.sidebar.success(f"Apify bağlı ({masked_token()})")
else:
    st.sidebar.warning("Apify token tanımlı değil — **Demo Mod**")
    st.sidebar.caption("Gerçek arama yapılmaz; sabit demo veriler gösterilir.")

st.sidebar.divider()
st.sidebar.page_link("streamlit_app.py",            label="← Ana Sayfa",         icon="🏠")
st.sidebar.page_link("pages/4_Business_Panel.py",   label="İşletme Paneli",       icon="📊")
st.sidebar.page_link("pages/6_Campaign_Automation.py", label="Kampanya Otomasyonu", icon="📣")

# ─── Başlık ───────────────────────────────────────────────────────────────────

st.title("🏢 İşletme Onboarding")
st.caption("Google Maps üzerinden otelinizi bulun ve SuggesMe platformuna kaydedin.")

tab_new, tab_list = st.tabs(["➕ Yeni İşletme Kaydı", "📋 Kayıtlı İşletmeler"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Kayıt sihirbazı
# ══════════════════════════════════════════════════════════════════════════════
with tab_new:

    step = st.session_state["ob_step"]

    # ── Adım göstergesi ──────────────────────────────────────────────────────
    steps = ["1 · Arama", "2 · Seçim", "3 · Bilgiler", "4 · Tamamlandı"]
    cols_ind = st.columns(len(steps))
    for i, (col, label) in enumerate(zip(cols_ind, steps), start=1):
        col.markdown(
            f"**{label}**" if i == step else f"<span style='color:gray'>{label}</span>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # ADIM 1 — Arama formu
    # ─────────────────────────────────────────────────────────────────────────
    if step == 1:
        st.subheader("Otelinizi Arayın")
        st.write("Otel adını, şehri ve ilçeyi girerek Google Maps'te arama yapın.")

        with st.form("search_form"):
            col_name, col_city, col_dist = st.columns([3, 2, 2])
            hotel_name = col_name.text_input("Otel Adı *", placeholder="Örn: Sürmeli Hotel")
            city       = col_city.text_input("Şehir *",    placeholder="Örn: İstanbul")
            district   = col_dist.text_input("İlçe",       placeholder="Örn: Beşiktaş")
            max_res    = st.slider("Maksimum sonuç sayısı", 1, 10, 5)
            submitted  = st.form_submit_button("🔍 Ara", use_container_width=True, type="primary")

        if submitted:
            if not hotel_name.strip() or not city.strip():
                st.error("Otel adı ve şehir zorunludur.")
            else:
                query = f"{hotel_name.strip()} {city.strip()}"
                if district.strip():
                    query += f" {district.strip()}"

                with st.spinner("Google Maps'te aranıyor…"):
                    try:
                        results = search_places(query, max_results=max_res)
                    except ValueError as exc:
                        st.error(str(exc))
                        results = []

                if not results:
                    st.warning("Sonuç bulunamadı. Arama terimini değiştirerek tekrar deneyin.")
                else:
                    st.session_state["ob_results"]        = results
                    st.session_state["ob_query_city"]     = city.strip()
                    st.session_state["ob_query_district"] = district.strip()
                    st.session_state["ob_step"]           = 2
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # ADIM 2 — Sonuç seçimi
    # ─────────────────────────────────────────────────────────────────────────
    elif step == 2:
        results = st.session_state.get("ob_results", [])
        st.subheader(f"Otelinizi Seçin ({len(results)} sonuç)")

        if not results:
            st.warning("Sonuç verisi kayboldu. Lütfen tekrar arayın.")
            if st.button("← Aramaya Dön"):
                _reset_flow()
                st.rerun()
        else:
            for i, place in enumerate(results):
                with st.container(border=True):
                    col_info, col_btn = st.columns([5, 1])
                    with col_info:
                        rating_str = f"⭐ {place['rating']}" if place.get("rating") else ""
                        reviews_str = f"({place['review_count']} yorum)" if place.get("review_count") else ""
                        st.markdown(f"**{place['name']}** {rating_str} {reviews_str}")
                        st.caption(place.get("address", ""))
                        detail_parts = []
                        if place.get("phone"):
                            detail_parts.append(f"📞 {place['phone']}")
                        if place.get("website"):
                            detail_parts.append(f"🌐 {place['website']}")
                        if place.get("category"):
                            detail_parts.append(f"🏷️ {place['category']}")
                        if detail_parts:
                            st.caption("  ·  ".join(detail_parts))
                    with col_btn:
                        if st.button("Seç", key=f"select_{i}", use_container_width=True, type="primary"):
                            st.session_state["ob_selected"] = place
                            st.session_state["ob_step"]     = 3
                            st.rerun()

            st.write("")
            if st.button("← Aramaya Dön", use_container_width=False):
                _reset_flow()
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # ADIM 3 — Sahip bilgileri + kaydet
    # ─────────────────────────────────────────────────────────────────────────
    elif step == 3:
        place    = st.session_state.get("ob_selected", {})
        def_city = st.session_state.get("ob_query_city", "")
        def_dist = st.session_state.get("ob_query_district", "")

        st.subheader("İşletme ve Hesap Bilgilerini Girin")

        with st.container(border=True):
            st.markdown(f"**Seçilen İşletme:** {place.get('name', '')}")
            st.caption(place.get("address", ""))
            if place.get("google_maps_url"):
                st.markdown(f"[Google Maps'te Görüntüle]({place['google_maps_url']})")

        st.write("")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Otel Detayları**")
            city      = st.text_input("Şehir *",        value=def_city)
            district  = st.text_input("İlçe",           value=def_dist)
            stars     = st.selectbox("Yıldız Sayısı *", [3, 4, 5], index=1)
            price_map = {"Ekonomik (budget)": "budget", "Orta (mid)": "mid", "Lüks (luxury)": "luxury"}
            price_lbl = st.selectbox("Fiyat Seviyesi *", list(price_map.keys()), index=1)
            price_level = price_map[price_lbl]

        with col_right:
            st.markdown("**Sahip Bilgileri**")
            owner_name  = st.text_input("Ad Soyad *",   placeholder="Ahmet Yılmaz")
            owner_email = st.text_input("E-posta",       placeholder="ahmet@otelim.com")
            owner_phone = st.text_input("Telefon",       placeholder="+90 5xx xxx xx xx")

        st.write("")
        col_back, col_save = st.columns([1, 3])

        with col_back:
            if st.button("← Geri", use_container_width=True):
                st.session_state["ob_step"] = 2
                st.rerun()

        with col_save:
            if st.button("💾 Kaydet ve Tamamla", use_container_width=True, type="primary"):
                if not city.strip() or not owner_name.strip():
                    st.error("Şehir ve Ad Soyad alanları zorunludur.")
                else:
                    extra = {
                        "city":        city.strip(),
                        "district":    district.strip(),
                        "stars":       stars,
                        "price_level": price_level,
                    }
                    try:
                        with st.spinner("İşletme kaydediliyor…"):
                            existing = find_existing_hotel(place)
                            if existing:
                                hotel_id = existing.id
                                st.session_state["ob_matched"] = existing.name
                            else:
                                hotel_id = create_hotel_from_place(place, extra)
                                st.session_state["ob_matched"] = None

                            register_business_account(
                                hotel_id=hotel_id,
                                owner_name=owner_name.strip(),
                                owner_email=owner_email.strip() or None,
                                owner_phone=owner_phone.strip() or None,
                                place=place,
                            )

                        st.session_state["ob_saved_hotel"] = place.get("name", "")
                        st.session_state["ob_step"] = 4
                        st.session_state.pop("ob_businesses", None)  # listeyi yenile
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Kayıt sırasında hata oluştu: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # ADIM 4 — Başarı
    # ─────────────────────────────────────────────────────────────────────────
    elif step == 4:
        hotel_name = st.session_state.get("ob_saved_hotel", "")
        matched    = st.session_state.get("ob_matched")

        st.success(f"**{hotel_name}** başarıyla sisteme kaydedildi!")

        if matched:
            st.info(f"Bu otel sistemde zaten mevcut ('**{matched}**') — sahip bilgileri güncellendi.")

        st.write("")
        col_a, col_b, col_c = st.columns(3)
        col_a.page_link("pages/4_Business_Panel.py",      label="→ İşletme Paneli",       icon="📊")
        col_b.page_link("pages/6_Campaign_Automation.py", label="→ Kampanya Otomasyonu",   icon="📣")

        with col_c:
            if st.button("➕ Yeni İşletme Kaydet", use_container_width=True):
                _reset_flow()
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Kayıtlı işletmeler
# ══════════════════════════════════════════════════════════════════════════════
with tab_list:
    st.subheader("Kayıtlı İşletmeler")

    if "ob_businesses" not in st.session_state:
        st.session_state["ob_businesses"] = get_registered_businesses()

    businesses = st.session_state["ob_businesses"]

    if not businesses:
        st.info('Henüz kayıtlı işletme yok. "Yeni İşletme Kaydı" sekmesinden başlayın.')
    else:
        df = pd.DataFrame(businesses).rename(columns={
            "id":           "ID",
            "hotel_name":   "Otel",
            "city":         "Şehir",
            "district":     "İlçe",
            "rating":       "Rating",
            "owner_name":   "İşletme Sahibi",
            "owner_email":  "E-posta",
            "verified":     "Doğrulandı",
            "created_at":   "Kayıt Tarihi",
        })

        st.metric("Toplam Kayıt", len(df))
        st.dataframe(
            df[["ID", "Otel", "Şehir", "İlçe", "Rating",
                "İşletme Sahibi", "E-posta", "Doğrulandı", "Kayıt Tarihi"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rating":       st.column_config.NumberColumn("Rating", format="%.1f"),
                "Doğrulandı":   st.column_config.CheckboxColumn("Doğrulandı"),
                "Kayıt Tarihi": st.column_config.DatetimeColumn("Kayıt Tarihi", format="DD.MM.YYYY HH:mm"),
            },
        )

        if st.button("🔄 Listeyi Yenile"):
            st.session_state.pop("ob_businesses", None)
            st.rerun()
