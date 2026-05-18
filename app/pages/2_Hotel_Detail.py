"""
Otel Detay Sayfası — seçilen otelin tam profili, harita, özellikler ve CTA butonları.

Özellikler:
  - Dropdown ile otel seçimi (Discovery'den session_state üzerinden de geçilebilir)
  - Rating, fiyat, konum, özellikler
  - Harita konumu (st.map)
  - Küratör notu (Sprint 5 için yer tutucu)
  - Basit kural tabanlı benzer otel önerileri
  - CTA butonları + user_events event tracking
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.crm.models import Hotel
from src.database.db import get_db
from src.utils.logger import get_logger
from src.utils.st_helpers import get_or_create_demo_user, track_event

logger = get_logger(__name__)

# ─── Görüntü sabitleri ────────────────────────────────────────────────────────

_STARS_ICON: dict[int, str] = {
    1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐",
}

_BUDGET_TR: dict[str, str] = {
    "budget":  "💰 Ekonomik",
    "mid":     "💳 Orta Segment",
    "luxury":  "💎 Lüks",
}

_AMENITY_TR: dict[str, str] = {
    "wifi":             "WiFi",
    "pool":             "Havuz",
    "spa":              "Spa",
    "gym":              "Fitness",
    "restaurant":       "Restoran",
    "bar":              "Bar",
    "beach_access":     "Plaj Erişimi",
    "kids_club":        "Çocuk Kulübü",
    "parking":          "Otopark",
    "room_service":     "Oda Servisi",
    "concierge":        "Concierge",
    "hammam":           "Hamam",
    "tennis":           "Tenis",
    "water_sports":     "Su Sporları",
    "meeting_room":     "Toplantı Salonu",
    "airport_shuttle":  "Havalimanı Servisi",
    "yoga":             "Yoga",
    "sauna":            "Sauna",
    "animation":        "Animasyon",
    "snorkeling":       "Şnorkel",
    "sunbed":           "Şezlong",
    "hiking_tours":     "Doğa Yürüyüşü",
    "hot_air_balloon":  "Sıcak Hava Balonu",
    "air_conditioning": "Klima",
    "tv":               "TV",
    "business_center":  "İş Merkezi",
    "playground":       "Oyun Parkı",
    "baby_cot":         "Bebek Yatağı",
    "meditation":       "Meditasyon",
    "water_sports":     "Su Sporları",
}

_PROFILE_TR: dict[str, str] = {
    "luxury_traveler":   "💎 Lüks",
    "family_vacation":   "👨‍👩‍👧 Aile",
    "budget_traveler":   "💰 Ekonomik",
    "honeymoon":         "💑 Balayı",
    "business_traveler": "💼 İş Seyahati",
    "wellness_spa":      "🧘 Spa & Wellness",
}

# ─── Veri nesnesi ─────────────────────────────────────────────────────────────

@dataclass
class HotelDetail:
    """ORM session kapandıktan sonra da güvenle kullanılabilen otel nesnesi."""
    id:           int
    name:         str
    city:         str
    district:     str
    address:      str
    rating:       float
    review_count: int
    stars:        int
    price_level:  str
    price_min:    float
    price_max:    float
    description:  str
    amenities:    list[str]
    profile_tags: list[str]
    latitude:     float | None
    longitude:    float | None
    website_url:  str | None
    booking_url:  str | None
    whatsapp_url: str | None
    phone:        str | None


# ─── Veri fonksiyonları ────────────────────────────────────────────────────────

def _load_hotel_index() -> list[tuple[int, str]]:
    """(id, isim) çiftleri — selectbox için. Session'da cache'lenir."""
    if "hotel_index" in st.session_state:
        return st.session_state["hotel_index"]
    try:
        with get_db() as db:
            rows = (
                db.query(Hotel.id, Hotel.name, Hotel.city)
                .filter(Hotel.is_active == True)
                .order_by(Hotel.city, Hotel.name)
                .all()
            )
            index = [(r.id, f"{r.name}  —  {r.city}") for r in rows]
        st.session_state["hotel_index"] = index
        return index
    except Exception as exc:
        logger.error("Otel dizini yüklenemedi: %s", exc)
        return []


def _load_hotel(hotel_id: int) -> HotelDetail | None:
    """Tek bir oteli yükler; session'da id bazlı cache'lenir."""
    cache_key = f"hotel_detail_{hotel_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        with get_db() as db:
            h = db.query(Hotel).filter(Hotel.id == hotel_id).first()
            if h is None:
                return None
            detail = HotelDetail(
                id=h.id, name=h.name, city=h.city, district=h.district,
                address=h.address or f"{h.district}, {h.city}",
                rating=h.rating or 0.0, review_count=h.review_count or 0,
                stars=h.stars or 3, price_level=h.price_level or "mid",
                price_min=h.price_min or 0.0, price_max=h.price_max or 0.0,
                description=h.description or "",
                amenities=json.loads(h.amenities or "[]"),
                profile_tags=json.loads(h.profile_tags or "[]"),
                latitude=h.latitude, longitude=h.longitude,
                website_url=h.website_url, booking_url=h.booking_url,
                whatsapp_url=h.whatsapp_url, phone=h.phone,
            )
        st.session_state[cache_key] = detail
        return detail
    except Exception as exc:
        logger.error("Otel yüklenemedi (id=%d): %s", hotel_id, exc)
        return None


def _load_all_for_similar() -> list[HotelDetail]:
    """Benzer otel hesabı için tüm otelleri yükler; session'da cache'lenir."""
    if "all_hotels_similar" in st.session_state:
        return st.session_state["all_hotels_similar"]
    try:
        with get_db() as db:
            rows = db.query(Hotel).filter(Hotel.is_active == True).all()
            all_h = [
                HotelDetail(
                    id=h.id, name=h.name, city=h.city, district=h.district,
                    address=h.address or "", rating=h.rating or 0.0,
                    review_count=h.review_count or 0, stars=h.stars or 3,
                    price_level=h.price_level or "mid",
                    price_min=h.price_min or 0.0, price_max=h.price_max or 0.0,
                    description=h.description or "",
                    amenities=json.loads(h.amenities or "[]"),
                    profile_tags=json.loads(h.profile_tags or "[]"),
                    latitude=h.latitude, longitude=h.longitude,
                    website_url=h.website_url, booking_url=h.booking_url,
                    whatsapp_url=h.whatsapp_url, phone=h.phone,
                )
                for h in rows
            ]
        st.session_state["all_hotels_similar"] = all_h
        return all_h
    except Exception as exc:
        logger.error("Benzer otel verisi yüklenemedi: %s", exc)
        return []


# ─── Benzer otel önerisi ──────────────────────────────────────────────────────

def _find_similar(hotel: HotelDetail, all_hotels: list[HotelDetail], top_n: int = 3) -> list[HotelDetail]:
    """
    Basit kural tabanlı benzerlik skoru:
      +2  aynı şehir
      +1  aynı fiyat seviyesi
      +1  her ortak profil etiketi
    Eşit skorlarda rating'e göre sıralanır.
    """
    scored: list[tuple[int, HotelDetail]] = []
    target_profiles = set(hotel.profile_tags)

    for h in all_hotels:
        if h.id == hotel.id:
            continue
        score = 0
        if h.city == hotel.city:
            score += 2
        if h.price_level == hotel.price_level:
            score += 1
        score += len(set(h.profile_tags) & target_profiles)
        scored.append((score, h))

    scored.sort(key=lambda t: (-t[0], -t[1].rating))
    return [h for _, h in scored[:top_n]]


# ─── UI bileşenleri ────────────────────────────────────────────────────────────

def _render_header(hotel: HotelDetail) -> None:
    stars = _STARS_ICON.get(hotel.stars, "")
    st.title(f"{stars} {hotel.name}")
    st.caption(f"📍 {hotel.city} / {hotel.district}  ·  {hotel.address}")


def _render_metrics(hotel: HotelDetail) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⭐ Rating",   f"{hotel.rating:.1f} / 5.0")
    m2.metric("💬 Yorum",   f"{hotel.review_count:,}")
    m3.metric("🏷️ Segment", _BUDGET_TR.get(hotel.price_level, hotel.price_level))
    m4.metric("💵 Gecelik", f"${hotel.price_min:.0f} – ${hotel.price_max:.0f}")


def _render_cta(hotel: HotelDetail, user_id: int) -> None:
    """Aksiyon butonları — gerçek rezervasyon yok, sadece redirect simülasyonu."""
    st.subheader("🚀 Harekete Geç")
    b1, b2, b3, b4 = st.columns(4)

    # Rezervasyon
    with b1:
        if st.button("📅 Rezervasyona Git", key="cta_res", use_container_width=True):
            track_event(user_id, hotel.id, "reservation_click",
                        {"hotel_name": hotel.name, "booking_url": hotel.booking_url})
            st.session_state["cta_res_open"] = True
        if st.session_state.get("cta_res_open"):
            if hotel.booking_url:
                st.link_button("→ Booking Sayfasına Aç", hotel.booking_url,
                               use_container_width=True)
            else:
                st.caption("*Rezervasyon linki mevcut değil*")

    # WhatsApp
    with b2:
        if st.button("💬 WhatsApp ile Yaz", key="cta_wa", use_container_width=True):
            track_event(user_id, hotel.id, "whatsapp_click",
                        {"hotel_name": hotel.name, "phone": hotel.phone})
            st.session_state["cta_wa_open"] = True
        if st.session_state.get("cta_wa_open"):
            if hotel.whatsapp_url:
                st.link_button("→ WhatsApp'ı Aç", hotel.whatsapp_url,
                               use_container_width=True)
            else:
                st.caption("*WhatsApp linki mevcut değil*")

    # Website
    with b3:
        if st.button("🌐 Websiteye Git", key="cta_web", use_container_width=True):
            track_event(user_id, hotel.id, "website_redirect",
                        {"hotel_name": hotel.name, "url": hotel.website_url})
            st.session_state["cta_web_open"] = True
        if st.session_state.get("cta_web_open"):
            if hotel.website_url:
                st.link_button("→ Websiteyi Aç", hotel.website_url,
                               use_container_width=True)
            else:
                st.caption("*Website linki mevcut değil*")

    # Favori
    with b4:
        fav_key   = f"detail_fav_{hotel.id}"
        is_fav    = st.session_state.get(fav_key, False)
        fav_label = "❤️ Favoride" if is_fav else "🤍 Favoriye Ekle"
        if st.button(fav_label, key="cta_fav", use_container_width=True):
            if not is_fav:
                track_event(user_id, hotel.id, "favorite_added",
                            {"hotel_name": hotel.name})
                st.session_state[fav_key] = True
                st.toast("❤️ Favorilere eklendi!", icon="✅")


def _render_map(hotel: HotelDetail) -> None:
    st.subheader("🗺️ Konum")
    if hotel.latitude and hotel.longitude:
        df = pd.DataFrame([{"lat": hotel.latitude, "lon": hotel.longitude}])
        st.map(df, zoom=13)
    else:
        st.info(f"📍 Harita verisi mevcut değil — Konum: **{hotel.city}**, {hotel.district}")


def _render_features(hotel: HotelDetail) -> None:
    st.subheader("🛎️ Özellikler ve Olanaklar")

    if not hotel.amenities:
        st.caption("Özellik bilgisi bulunamadı.")
        return

    # 3 sütunda göster
    chunk = max(1, len(hotel.amenities) // 3 + 1)
    cols = st.columns(3)
    for i, am in enumerate(hotel.amenities):
        label = _AMENITY_TR.get(am, am.replace("_", " ").title())
        cols[i % 3].markdown(f"- ✅ {label}")

    if hotel.profile_tags:
        st.markdown("**👤 Uygun Misafir Profilleri:**  " +
                    "  ·  ".join(_PROFILE_TR.get(p, p) for p in hotel.profile_tags))


def _render_curator_note() -> None:
    """Küratör notu — Sprint 5'te küratör paneli tamamlanınca doldurulacak."""
    st.subheader("💬 Küratör Notu")
    with st.container(border=True):
        st.caption("*Küratör notu henüz eklenmemiş. Küratör paneli Sprint 5'te devreye giriyor.*")


def _render_similar(similar: list[HotelDetail], user_id: int) -> None:
    if not similar:
        return

    st.subheader("🔄 Benzer Oteller")
    cols = st.columns(len(similar))

    for col, h in zip(cols, similar):
        with col:
            with st.container(border=True):
                stars = _STARS_ICON.get(h.stars, "")
                st.markdown(f"**{stars} {h.name}**")
                st.caption(f"📍 {h.city} / {h.district}")
                c1, c2 = st.columns(2)
                c1.caption(f"★ {h.rating:.1f}")
                c2.caption(_BUDGET_TR.get(h.price_level, ""))

                if h.amenities:
                    top_ams = [_AMENITY_TR.get(a, a) for a in h.amenities[:3]]
                    st.caption("  ·  ".join(f"`{a}`" for a in top_ams))

                if st.button("🔍 Detay Gör", key=f"sim_{h.id}", use_container_width=True):
                    track_event(user_id, h.id, "hotel_view",
                                {"source": "similar_hotels", "hotel_name": h.name})
                    # Seçili oteli güncelle, CTA state'lerini temizle
                    for k in ["cta_res_open", "cta_wa_open", "cta_web_open"]:
                        st.session_state.pop(k, None)
                    st.session_state["selected_hotel_id"] = h.id
                    st.rerun()


# ─── Sayfa giriş noktası ──────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Otel Detay | SuggesMe",
        page_icon="🏨",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    user_id = get_or_create_demo_user()

    # ── Otel dizini ───────────────────────────────────────────────────────────
    hotel_index = _load_hotel_index()

    if not hotel_index:
        st.warning("⚠️ Henüz otel verisi bulunamadı.")
        st.code("python scripts/generate_synthetic_data.py --reset", language="bash")
        st.stop()

    # ── Otel seçimi ───────────────────────────────────────────────────────────
    # Discovery sayfasından gelen session_state değeri varsa ön seçim yap
    id_list   = [hid for hid, _ in hotel_index]
    name_list = [name for _, name in hotel_index]

    preselect_id  = st.session_state.get("selected_hotel_id")
    default_index = id_list.index(preselect_id) if preselect_id in id_list else 0

    st.sidebar.header("🏨 Otel Seç")
    chosen_name = st.sidebar.selectbox(
        "Otel",
        name_list,
        index=default_index,
        label_visibility="collapsed",
    )
    selected_id = id_list[name_list.index(chosen_name)]

    # Selectbox değiştiğinde CTA buton state'lerini temizle
    if st.session_state.get("_last_hotel_id") != selected_id:
        for k in ["cta_res_open", "cta_wa_open", "cta_web_open"]:
            st.session_state.pop(k, None)
        st.session_state["_last_hotel_id"]    = selected_id
        st.session_state["selected_hotel_id"] = selected_id

    st.sidebar.divider()
    st.sidebar.page_link("pages/1_Discovery.py", label="← Keşfe Dön", icon="🔍")

    # ── Otel yükleme ──────────────────────────────────────────────────────────
    hotel = _load_hotel(selected_id)

    if hotel is None:
        st.error("Otel bilgisi yüklenemedi. Lütfen başka bir otel seçin.")
        st.stop()

    # ── hotel_view — sayfa açılışında yalnızca bir kez kaydedilir ─────────────
    view_key = f"detail_page_viewed_{hotel.id}"
    if not st.session_state.get(view_key):
        track_event(user_id, hotel.id, "hotel_view",
                    {"source": "detail_page", "hotel_name": hotel.name})
        st.session_state[view_key] = True

    # ── İçerik ────────────────────────────────────────────────────────────────
    _render_header(hotel)
    st.divider()
    _render_metrics(hotel)

    st.write("")
    _render_cta(hotel, user_id)

    st.divider()
    left_col, right_col = st.columns([1, 1])

    with left_col:
        _render_features(hotel)
        st.write("")
        _render_curator_note()

    with right_col:
        _render_map(hotel)

    st.divider()

    all_hotels = _load_all_for_similar()
    similar    = _find_similar(hotel, all_hotels)
    _render_similar(similar, user_id)


main()
