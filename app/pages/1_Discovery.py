"""
Otel Keşif Sayfası — son kullanıcı için filtrelenebilir otel listesi.

Özellikler:
  - Şehir / ilçe / bütçe / seyahat tipi / rating / özellik filtreleri
  - Otel kartları (metrikler, özellikler, aksiyon butonları)
  - user_events tablosuna event tracking
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from src.crm.models import Hotel
from src.database.db import get_db
from src.utils.logger import get_logger
from src.utils.st_helpers import get_or_create_demo_user as _get_or_create_demo_user
from src.utils.st_helpers import track_event as _track

logger = get_logger(__name__)

# ─── Çeviri / görüntü sabitleri ──────────────────────────────────────────────

_PROFILE_TR: dict[str, str] = {
    "luxury_traveler":   "💎 Lüks",
    "family_vacation":   "👨‍👩‍👧 Aile",
    "budget_traveler":   "💰 Ekonomik",
    "honeymoon":         "💑 Balayı",
    "business_traveler": "💼 İş Seyahati",
    "wellness_spa":      "🧘 Spa & Wellness",
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
}

_STARS_ICON: dict[int, str] = {
    1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐",
}


# ─── Veri nesnesi ─────────────────────────────────────────────────────────────

@dataclass
class HotelCard:
    """
    ORM oturumu kapandıktan sonra da güvenle kullanılabilen
    otel görüntüleme nesnesi.
    """
    id:           int
    name:         str
    city:         str
    district:     str
    rating:       float
    review_count: int
    stars:        int
    price_level:  str
    price_min:    float
    price_max:    float
    description:  str
    amenities:    list[str]
    profile_tags: list[str]
    website_url:  str | None
    booking_url:  str | None
    whatsapp_url: str | None
    phone:        str | None


# ─── Veri fonksiyonları ────────────────────────────────────────────────────────

def _load_all_hotels() -> list[HotelCard]:
    """
    Tüm aktif otelleri DB'den çeker.
    Aynı tarayıcı oturumunda tekrar sorgu atmaz (session_state cache).

    NOT: @st.cache_data burada kullanılamaz; sayfa dosyası '1_' ile
    başladığı için Python geçersiz modül yolu oluşturuyor ve pickle
    HotelCard sınıfını serileştiremez (UnserializableReturnValueError).
    """
    if "hotels_cache" in st.session_state:
        return st.session_state["hotels_cache"]

    try:
        with get_db() as db:
            rows = db.query(Hotel).filter(Hotel.is_active == True).all()
            result = [
                HotelCard(
                    id=h.id, name=h.name, city=h.city, district=h.district,
                    rating=h.rating or 0.0, review_count=h.review_count or 0,
                    stars=h.stars or 3, price_level=h.price_level or "mid",
                    price_min=h.price_min or 0.0, price_max=h.price_max or 0.0,
                    description=h.description or "",
                    amenities=json.loads(h.amenities or "[]"),
                    profile_tags=json.loads(h.profile_tags or "[]"),
                    website_url=h.website_url, booking_url=h.booking_url,
                    whatsapp_url=h.whatsapp_url, phone=h.phone,
                )
                for h in rows
            ]
        st.session_state["hotels_cache"] = result
        return result
    except Exception as exc:
        logger.error("Otel yüklenemedi: %s", exc)
        return []


def _apply_filters(
    hotels:       list[HotelCard],
    city:         str | None,
    district:     str | None,
    price_level:  str | None,
    travel_type:  str | None,
    min_rating:   float,
    amenity_tags: list[str],
) -> list[HotelCard]:
    """Bellek içi filtreleme; DB'ye tekrar gidilmez."""
    result = hotels

    if city:
        result = [h for h in result if h.city == city]
    if district:
        result = [h for h in result if h.district == district]
    if price_level:
        result = [h for h in result if h.price_level == price_level]
    if min_rating > 0:
        result = [h for h in result if h.rating >= min_rating]
    if travel_type:
        result = [h for h in result if travel_type in h.profile_tags]
    if amenity_tags:
        result = [h for h in result if all(a in h.amenities for a in amenity_tags)]

    return result


# _get_or_create_demo_user ve _track → src.utils.st_helpers'dan import edildi


# ─── Kart bileşeni ────────────────────────────────────────────────────────────

def _render_hotel_card(hotel: HotelCard, user_id: int) -> None:
    """Tek bir otel kartını render eder."""

    with st.container(border=True):

        # ── 1. Başlık ─────────────────────────────────────────────────────
        title_col, loc_col = st.columns([3, 1])
        with title_col:
            stars = _STARS_ICON.get(hotel.stars, "")
            st.markdown(f"### {stars} {hotel.name}")
        with loc_col:
            st.markdown(f"<div style='text-align:right;padding-top:8px'>📍 <b>{hotel.city}</b> / {hotel.district}</div>",
                        unsafe_allow_html=True)

        # ── 2. Metrikler ──────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("⭐ Rating", f"{hotel.rating:.1f} / 5.0")
        m2.metric("💬 Yorum", f"{hotel.review_count:,}")
        m3.metric("🏷️ Segment", _BUDGET_TR.get(hotel.price_level, hotel.price_level))
        m4.metric("💵 Gecelik", f"${hotel.price_min:.0f} – ${hotel.price_max:.0f}")

        # ── 3. Öne çıkan özellikler (max 6) ─────────────────────────────
        if hotel.amenities:
            tags = [
                _AMENITY_TR.get(a, a.replace("_", " ").title())
                for a in hotel.amenities[:6]
            ]
            st.caption("**Özellikler:** " + "  ·  ".join(f"`{t}`" for t in tags))

        # ── 4. Açıklama ───────────────────────────────────────────────────
        if hotel.description:
            st.caption(hotel.description)

        # ── 5. Küratör notu (placeholder — Sprint 5'te doldurulacak) ─────
        st.caption("💬 **Küratör Notu:** *(Küratör paneli Sprint 5'te ekleniyor)*")

        st.write("")  # hafif boşluk

        # ── 6. Aksiyon butonları ──────────────────────────────────────────
        b_res, b_wa, b_web, b_fav, b_det = st.columns(5)

        # Rezervasyon
        with b_res:
            if st.button("📅 Rezervasyon", key=f"res_{hotel.id}", use_container_width=True):
                _track(user_id, hotel.id, "reservation_click",
                       {"hotel_name": hotel.name, "booking_url": hotel.booking_url})
                st.session_state[f"res_open_{hotel.id}"] = True

            if st.session_state.get(f"res_open_{hotel.id}"):
                if hotel.booking_url:
                    st.link_button("→ Rezervasyona Git", hotel.booking_url,
                                   use_container_width=True)
                else:
                    st.caption("*Link mevcut değil*")

        # WhatsApp
        with b_wa:
            if st.button("💬 WhatsApp", key=f"wa_{hotel.id}", use_container_width=True):
                _track(user_id, hotel.id, "whatsapp_click",
                       {"hotel_name": hotel.name, "phone": hotel.phone})
                st.session_state[f"wa_open_{hotel.id}"] = True

            if st.session_state.get(f"wa_open_{hotel.id}"):
                if hotel.whatsapp_url:
                    st.link_button("→ WhatsApp'ı Aç", hotel.whatsapp_url,
                                   use_container_width=True)
                else:
                    st.caption("*Link mevcut değil*")

        # Website
        with b_web:
            if st.button("🌐 Website", key=f"web_{hotel.id}", use_container_width=True):
                _track(user_id, hotel.id, "website_redirect",
                       {"hotel_name": hotel.name, "url": hotel.website_url})
                st.session_state[f"web_open_{hotel.id}"] = True

            if st.session_state.get(f"web_open_{hotel.id}"):
                if hotel.website_url:
                    st.link_button("→ Websiteye Git", hotel.website_url,
                                   use_container_width=True)
                else:
                    st.caption("*Link mevcut değil*")

        # Favori
        with b_fav:
            fav_key    = f"fav_{hotel.id}"
            is_fav     = st.session_state.get(fav_key, False)
            fav_label  = "❤️ Favoride" if is_fav else "🤍 Favoriye Ekle"
            if st.button(fav_label, key=f"favbtn_{hotel.id}", use_container_width=True):
                if not is_fav:
                    _track(user_id, hotel.id, "favorite_added",
                           {"hotel_name": hotel.name})
                    st.session_state[fav_key] = True
                    st.toast("❤️ Favorilere eklendi!", icon="✅")

        # Detay
        with b_det:
            det_key = f"detail_{hotel.id}"
            det_lbl = "🔼 Gizle" if st.session_state.get(det_key) else "🔍 Detay"
            if st.button(det_lbl, key=f"detbtn_{hotel.id}", use_container_width=True):
                new_state = not st.session_state.get(det_key, False)
                st.session_state[det_key] = new_state
                # hotel_view yalnızca ilk açılışta kaydedilir
                if new_state and not st.session_state.get(f"viewed_{hotel.id}"):
                    _track(user_id, hotel.id, "hotel_view",
                           {"hotel_name": hotel.name, "city": hotel.city})
                    st.session_state[f"viewed_{hotel.id}"] = True

        # ── 7. Detay paneli ───────────────────────────────────────────────
        if st.session_state.get(f"detail_{hotel.id}"):
            st.divider()
            dc1, dc2 = st.columns(2)

            with dc1:
                st.markdown("**🛎️ Tüm Olanak ve Özellikler**")
                for am in hotel.amenities:
                    label = _AMENITY_TR.get(am, am.replace("_", " ").title())
                    st.markdown(f"- ✅ {label}")

            with dc2:
                st.markdown("**👤 Uygun Misafir Profilleri**")
                for pt in hotel.profile_tags:
                    st.markdown(f"- {_PROFILE_TR.get(pt, pt)}")

                st.markdown("---")
                if hotel.phone:
                    st.markdown(f"📞 **Telefon:** {hotel.phone}")
                if hotel.address:
                    st.markdown(f"📌 **Adres:** {hotel.address}")


# ─── Kenar çubuğu ─────────────────────────────────────────────────────────────

def _render_sidebar(all_hotels: list[HotelCard]) -> dict:
    """Filtre seçeneklerini sidebar'a çizer, seçilen değerleri döndürür."""

    cities = sorted({h.city for h in all_hotels})
    all_ams: set[str] = set()
    for h in all_hotels:
        all_ams.update(h.amenities)
    am_display = {
        _AMENITY_TR.get(a, a.replace("_", " ").title()): a
        for a in sorted(all_ams)
    }

    with st.sidebar:
        st.header("🔎 Filtreler")

        selected_city = st.selectbox(
            "Şehir",
            [""] + cities,
            format_func=lambda x: "— Tümü —" if x == "" else x,
            key="f_city",
        )

        district_opts = sorted({h.district for h in all_hotels if h.city == selected_city}) \
            if selected_city else []
        selected_district = st.selectbox(
            "İlçe",
            [""] + district_opts,
            format_func=lambda x: "— Tümü —" if x == "" else x,
            disabled=not selected_city,
            key="f_district",
        )

        selected_budget = st.selectbox(
            "Bütçe Seviyesi",
            ["", "budget", "mid", "luxury"],
            format_func=lambda x: "— Tümü —" if x == "" else _BUDGET_TR.get(x, x),
            key="f_budget",
        )

        selected_travel = st.selectbox(
            "Seyahat Tipi",
            [""] + list(_PROFILE_TR.keys()),
            format_func=lambda x: "— Tümü —" if x == "" else _PROFILE_TR.get(x, x),
            key="f_travel",
        )

        min_rating = st.slider(
            "Minimum Rating", 0.0, 5.0, 0.0, 0.5,
            key="f_rating",
        )

        selected_ams_display = st.multiselect(
            "Olanak / Özellik",
            sorted(am_display.keys()),
            key="f_amenities",
        )
        selected_amenities = [am_display[d] for d in selected_ams_display]

        st.divider()
        if st.button("🔄 Sıfırla", use_container_width=True):
            for k in ["hotels_cache", "f_city", "f_district", "f_budget", "f_travel", "f_rating", "f_amenities"]:
                st.session_state.pop(k, None)
            st.rerun()

        st.divider()
        st.caption(f"Toplam {len(all_hotels)} otel listelendi.")

    return {
        "city":       selected_city or None,
        "district":   selected_district or None,
        "price_level":selected_budget or None,
        "travel_type":selected_travel or None,
        "min_rating": min_rating,
        "amenity_tags": selected_amenities,
    }


# ─── Sıralama ─────────────────────────────────────────────────────────────────

def _sort_hotels(hotels: list[HotelCard], sort_by: str) -> list[HotelCard]:
    sorts = {
        "⭐ Rating (yüksekten)": lambda h: h.rating,
        "💬 Yorum (çoktan)":    lambda h: h.review_count,
        "💵 Fiyat (düşükten)":  lambda h: h.price_min,
        "💵 Fiyat (yüksekten)": lambda h: -h.price_max,
    }
    key = sorts.get(sort_by, lambda h: h.rating)
    reverse = sort_by not in ("💵 Fiyat (düşükten)",)
    return sorted(hotels, key=key, reverse=reverse)


# ─── Sayfa giriş noktası ──────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Otel Keşfet | SuggesMe",
        page_icon="🏨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏨 Otel Keşfet")
    st.caption("Küratörler tarafından seçilmiş otelleri filtreleyin, karşılaştırın ve harekete geçin.")

    # Demo kullanıcıyı başlat
    user_id = _get_or_create_demo_user()

    # Tüm otelleri yükle
    all_hotels = _load_all_hotels()

    if not all_hotels:
        st.warning(
            "⚠️ Henüz otel verisi bulunamadı. "
            "Lütfen önce aşağıdaki komutu çalıştırın:"
        )
        st.code("python scripts/generate_synthetic_data.py --reset", language="bash")
        st.stop()

    # Filtreler
    filters = _render_sidebar(all_hotels)

    # Filtreleme
    hotels = _apply_filters(all_hotels, **filters)

    # Üst çubuk: sonuç sayısı + sıralama
    top_left, top_right = st.columns([4, 2])
    with top_left:
        active_filters = sum(1 for v in filters.values() if v not in (None, [], 0.0))
        badge = f" · **{active_filters} filtre aktif**" if active_filters else ""
        st.markdown(f"**{len(hotels)} otel bulundu**{badge}")
    with top_right:
        sort_by = st.selectbox(
            "Sırala",
            ["⭐ Rating (yüksekten)", "💬 Yorum (çoktan)", "💵 Fiyat (düşükten)", "💵 Fiyat (yüksekten)"],
            label_visibility="collapsed",
        )

    hotels = _sort_hotels(hotels, sort_by)

    # Sonuç yok
    if not hotels:
        st.info(
            "🔍 Arama kriterlerinize uygun otel bulunamadı. "
            "Filtreleri değiştirerek tekrar deneyin."
        )
        st.stop()

    # Otel kartları
    for hotel in hotels:
        _render_hotel_card(hotel, user_id)
        st.write("")  # kartlar arası boşluk


main()
