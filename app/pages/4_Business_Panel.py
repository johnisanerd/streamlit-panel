"""
İşletme Paneli — Sprint 6

Otel sahiplerine performans KPI'ları, trafik grafikleri ve öneri içgörüleri sunar.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.express as px
import streamlit as st

from src.business.business_dashboard_service import (
    calc_competitor_comparison,
    calc_daily_trend,
    calc_event_distribution,
    calc_kpis,
    calc_profile_distribution,
    calc_recommendations,
    calc_top_hotels,
    load_all_hotel_events,
    load_hotel_events,
)
from src.crm.models import Hotel
from src.database.db import get_db

st.set_page_config(
    page_title="İşletme Paneli — SuggesMe",
    page_icon="📊",
    layout="wide",
)


# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def _load_hotel_index() -> list[Hotel]:
    if "biz_hotel_index" not in st.session_state:
        try:
            with get_db() as db:
                hotels = db.query(Hotel).filter(Hotel.is_active == True).order_by(Hotel.name).all()
                st.session_state["biz_hotel_index"] = [
                    {"id": h.id, "name": h.name, "city": h.city}
                    for h in hotels
                ]
        except Exception as exc:
            st.error(f"Otel listesi yüklenemedi: {exc}")
            st.session_state["biz_hotel_index"] = []
    return st.session_state["biz_hotel_index"]


def _render_sidebar(hotels: list[dict]) -> tuple[int, datetime, datetime]:
    st.sidebar.title("📊 İşletme Paneli")

    hotel_options = {h["id"]: f"{h['name']} ({h['city']})" for h in hotels}
    if not hotel_options:
        st.sidebar.warning("Aktif otel bulunamadı.")
        st.stop()

    selected_id = st.sidebar.selectbox(
        "Otel seçin",
        options=list(hotel_options.keys()),
        format_func=lambda hid: hotel_options[hid],
        key="biz_selected_hotel",
    )

    st.sidebar.divider()
    st.sidebar.subheader("📅 Tarih Aralığı")

    today = date.today()
    presets = {
        "Son 7 Gün":   timedelta(days=7),
        "Son 30 Gün":  timedelta(days=30),
        "Son 90 Gün":  timedelta(days=90),
        "Son 6 Ay":    timedelta(days=180),
        "Son 1 Yıl":   timedelta(days=365),
    }
    preset = st.sidebar.selectbox("Hızlı seçim", list(presets.keys()), index=1)
    delta = presets[preset]

    default_start = today - delta
    start_date = st.sidebar.date_input("Başlangıç", value=default_start, max_value=today)
    end_date   = st.sidebar.date_input("Bitiş",     value=today,          max_value=today)

    if start_date > end_date:
        st.sidebar.error("Başlangıç tarihi bitiş tarihinden büyük olamaz.")
        st.stop()

    st.sidebar.divider()
    st.sidebar.page_link("streamlit_app.py",      label="← Ana Sayfa",       icon="🏠")
    st.sidebar.page_link("pages/1_Discovery.py",  label="Otel Keşfet",        icon="🔍")
    st.sidebar.page_link("pages/3_Curator_Panel.py", label="Küratör Paneli",  icon="✍️")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date,   datetime.max.time())
    return selected_id, start_dt, end_dt


def _kpi_cards(kpis: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.metric("👁️ Görüntülenme",          f"{kpis['views']:,}")
    c2.metric("❤️ Favoriye Ekleme",        f"{kpis['favorites']:,}")
    c3.metric("📋 Rezervasyon Tıklaması",  f"{kpis['reservations']:,}")
    c4.metric("💬 WhatsApp Tıklaması",     f"{kpis['whatsapp']:,}")
    c5.metric("🌐 Website Yönlendirmesi",  f"{kpis['website']:,}")
    c6.metric("📈 Dönüşüm Oranı",          f"%{kpis['conversion_rate']}")


def _chart_daily_trend(df_trend) -> None:
    if df_trend.empty:
        st.info("Grafik için yeterli veri yok.")
        return
    fig = px.line(
        df_trend,
        x="Tarih",
        y="Sayı",
        color="Event Tipi",
        markers=True,
        title="Günlük Etkileşim Trendi",
    )
    fig.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)


def _chart_event_distribution(df_dist) -> None:
    if df_dist.empty:
        st.info("Grafik için yeterli veri yok.")
        return
    fig = px.bar(
        df_dist,
        x="Event Tipi",
        y="Sayı",
        text="Oran (%)",
        title="Event Tipi Dağılımı",
        color="Event Tipi",
    )
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Etkileşim Sayısı")
    st.plotly_chart(fig, use_container_width=True)


def _chart_profile_distribution(df_prof) -> None:
    if df_prof.empty:
        st.info("Grafik için yeterli veri yok.")
        return
    fig = px.pie(
        df_prof,
        names="Profil",
        values="Sayı",
        title="Kullanıcı Profil Dağılımı",
        hole=0.35,
    )
    fig.update_traces(textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)


def _chart_top_hotels(df_top) -> None:
    if df_top.empty:
        st.info("Grafik için yeterli veri yok.")
        return
    fig = px.bar(
        df_top,
        x="Toplam Etkileşim",
        y="Otel",
        orientation="h",
        color="Şehir",
        title="En Çok Etkileşim Alan Oteller",
        text="Toplam Etkileşim",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)


def _chart_competitor(df_comp) -> None:
    if df_comp.empty:
        st.info("Aynı şehirde karşılaştırma için yeterli otel/veri yok.")
        return

    df_melt = df_comp[["Otel", "Görüntülenme", "Rezervasyon", "Favori", "WhatsApp"]].melt(
        id_vars="Otel", var_name="Metrik", value_name="Değer"
    )

    selected_otel = df_comp.loc[df_comp["Seçili"] == True, "Otel"].values
    color_map = {}
    if len(selected_otel):
        for otel in df_comp["Otel"]:
            color_map[otel] = "#EF553B" if otel in selected_otel else "#636EFA"

    fig = px.bar(
        df_melt,
        x="Otel",
        y="Değer",
        color="Metrik",
        barmode="group",
        title="Şehir İçi Rakip Karşılaştırması",
    )
    fig.update_layout(legend_title_text="", xaxis_title="", yaxis_title="Etkileşim Sayısı")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_comp.drop(columns=["Seçili"]),
        use_container_width=True,
        hide_index=True,
    )


def _recommendation_boxes(recs: dict) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("#### 🎯 Kampanya Segmenti")
            st.markdown(recs["segment"])

    with col2:
        with st.container(border=True):
            st.markdown("#### ✨ Öne Çıkarılacak Özellik")
            st.markdown(recs["feature"])

    with col3:
        with st.container(border=True):
            st.markdown("#### 📣 En İyi CTA")
            st.markdown(recs["cta"])


# ─── Ana sayfa ────────────────────────────────────────────────────────────────

def main() -> None:
    hotels = _load_hotel_index()
    hotel_id, start_dt, end_dt = _render_sidebar(hotels)

    hotel_name = next((h["name"] for h in hotels if h["id"] == hotel_id), f"Otel #{hotel_id}")
    st.title(f"📊 İşletme Paneli — {hotel_name}")
    st.caption(
        f"{start_dt.strftime('%d.%m.%Y')} – {end_dt.strftime('%d.%m.%Y')} "
        "tarih aralığındaki veriler gösteriliyor."
    )

    # Veri yükleme
    cache_key_hotel  = f"biz_df_{hotel_id}_{start_dt.date()}_{end_dt.date()}"
    cache_key_all    = f"biz_all_{start_dt.date()}_{end_dt.date()}"

    if cache_key_hotel not in st.session_state:
        with st.spinner("Otel verileri yükleniyor…"):
            st.session_state[cache_key_hotel] = load_hotel_events(hotel_id, start_dt, end_dt)

    if cache_key_all not in st.session_state:
        with st.spinner("Platform verileri yükleniyor…"):
            st.session_state[cache_key_all] = load_all_hotel_events(start_dt, end_dt)

    df     = st.session_state[cache_key_hotel]
    all_df = st.session_state[cache_key_all]

    # ── KPI ──────────────────────────────────────────────────────────────────
    st.subheader("📌 Temel Metrikler")
    kpis = calc_kpis(df)
    _kpi_cards(kpis)

    if df.empty:
        st.warning("Seçilen otel ve tarih aralığı için hiç etkileşim verisi bulunamadı.")

    st.divider()

    # ── Grafikler ─────────────────────────────────────────────────────────────
    st.subheader("📈 Performans Grafikleri")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        _chart_daily_trend(calc_daily_trend(df))

    with col_right:
        _chart_event_distribution(calc_event_distribution(df))

    col_mid_left, col_mid_right = st.columns(2)

    with col_mid_left:
        _chart_profile_distribution(calc_profile_distribution(df))

    with col_mid_right:
        _chart_top_hotels(calc_top_hotels(all_df, limit=10))

    st.divider()

    st.subheader("🏆 Rakip Karşılaştırması")
    _chart_competitor(calc_competitor_comparison(hotel_id, all_df))

    st.divider()

    # ── Öneriler ─────────────────────────────────────────────────────────────
    st.subheader("💡 Akıllı Öneriler")
    recs = calc_recommendations(hotel_id, df, all_df)
    _recommendation_boxes(recs)


main()
