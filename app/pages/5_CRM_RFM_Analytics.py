"""
RFM Analitik Paneli — Sprint 7

Kullanıcı davranış verilerinden RFM segmentasyonu yapar;
segment dağılımını, özet istatistikleri ve kampanya önerilerini gösterir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.express as px
import streamlit as st

from src.crm.rfm_analysis import (
    SEGMENT_ORDER,
    calculate_rfm_scores,
    ensure_tables,
    get_last_calculation_time,
    get_rfm_table,
    get_segment_summary,
    save_rfm_scores,
)
from src.crm.models import CRMUser
from src.database.db import get_db

st.set_page_config(
    page_title="RFM Analizi — SuggesMe",
    page_icon="🎯",
    layout="wide",
)

ensure_tables()

# ─── Segment renk haritası ────────────────────────────────────────────────────

SEGMENT_COLORS = {
    "Champions":           "#2ECC71",
    "Loyal Customers":     "#27AE60",
    "Potential Loyalists": "#F1C40F",
    "New Customers":       "#3498DB",
    "At Risk":             "#E67E22",
    "Hibernating":         "#E74C3C",
    "Low Value":           "#95A5A6",
}

# ─── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("🎯 RFM Analizi")

last_calc = get_last_calculation_time()
if last_calc:
    st.sidebar.caption(f"Son analiz: {last_calc.strftime('%d.%m.%Y %H:%M')}")
else:
    st.sidebar.caption("Henüz analiz çalıştırılmadı.")

run_analysis = st.sidebar.button("🔄 Analizi Hesapla ve Kaydet", use_container_width=True, type="primary")

st.sidebar.divider()

all_segments = ["Tümü"] + SEGMENT_ORDER
seg_filter = st.sidebar.selectbox("Segment filtrele", all_segments)

st.sidebar.divider()
st.sidebar.page_link("streamlit_app.py",          label="← Ana Sayfa",      icon="🏠")
st.sidebar.page_link("pages/1_Discovery.py",       label="Otel Keşfet",       icon="🔍")
st.sidebar.page_link("pages/4_Business_Panel.py",  label="İşletme Paneli",    icon="📊")

# ─── Analiz tetikleme ─────────────────────────────────────────────────────────

if run_analysis:
    with st.spinner("RFM skorları hesaplanıyor…"):
        rfm_df = calculate_rfm_scores()
    if rfm_df.empty:
        st.error("Hesaplama için yeterli veri bulunamadı. Önce sentetik veri üretin.")
        st.stop()
    with st.spinner("Skorlar veritabanına kaydediliyor…"):
        saved = save_rfm_scores(rfm_df)
    st.success(f"{saved} kullanıcının RFM skoru güncellendi.")
    # Önbelleği temizle — tüm biz_* ve rfm_* anahtarlarını at
    for key in list(st.session_state.keys()):
        if key.startswith(("rfm_", "biz_")):
            st.session_state.pop(key)

# ─── Veri yükleme ─────────────────────────────────────────────────────────────

if "rfm_summary" not in st.session_state:
    st.session_state["rfm_summary"] = get_segment_summary()
if "rfm_table" not in st.session_state:
    st.session_state["rfm_table"] = get_rfm_table()

summary_df = st.session_state["rfm_summary"]
table_df   = st.session_state["rfm_table"]

# ─── Başlık ───────────────────────────────────────────────────────────────────

st.title("🎯 RFM Analizi — Kullanıcı Segmentasyonu")
st.caption(
    "Recency (son etkileşim), Frequency (etkileşim sıklığı) ve "
    "Monetary (proxy değer) metriklerine göre kullanıcılar segmentlere ayrılır."
)

if summary_df.empty:
    st.info("Henüz RFM verisi yok. Sol paneldeki **Analizi Hesapla ve Kaydet** butonuna basın.")
    st.stop()

# ─── KPI kartları ─────────────────────────────────────────────────────────────

st.subheader("📌 Genel Bakış")

total_users = 0
try:
    with get_db() as db:
        total_users = db.query(CRMUser).count()
except Exception:
    pass

analyzed     = int(summary_df["Kullanıcı Sayısı"].sum())
champions    = int(summary_df.loc[summary_df["Segment"] == "Champions",    "Kullanıcı Sayısı"].sum())
at_risk      = int(summary_df.loc[summary_df["Segment"] == "At Risk",      "Kullanıcı Sayısı"].sum())
hibernating  = int(summary_df.loc[summary_df["Segment"] == "Hibernating",  "Kullanıcı Sayısı"].sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👥 Toplam Kullanıcı",    f"{total_users:,}")
c2.metric("🔬 Analiz Edilen",       f"{analyzed:,}")
c3.metric("🏆 Champions",           f"{champions:,}")
c4.metric("⚠️ At Risk",             f"{at_risk:,}")
c5.metric("💤 Hibernating",         f"{hibernating:,}")

st.divider()

# ─── Grafikler ────────────────────────────────────────────────────────────────

st.subheader("📊 Segment Analizi")

col_pie, col_bar = st.columns(2)

with col_pie:
    fig_pie = px.pie(
        summary_df,
        names="Segment",
        values="Kullanıcı Sayısı",
        title="Segment Dağılımı",
        color="Segment",
        color_discrete_map=SEGMENT_COLORS,
        hole=0.35,
        category_orders={"Segment": SEGMENT_ORDER},
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    fig_bar = px.bar(
        summary_df,
        x="Segment",
        y="Ort. Monetary",
        title="Segment Bazlı Ortalama Monetary (Proxy ₺)",
        color="Segment",
        color_discrete_map=SEGMENT_COLORS,
        text="Ort. Monetary",
        category_orders={"Segment": SEGMENT_ORDER},
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(showlegend=False, xaxis_title="", yaxis_title="Ort. Monetary")
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ─── Segment özet tablosu + kampanya önerileri ────────────────────────────────

st.subheader("📋 Segment Özeti ve Kampanya Önerileri")

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Segment":            st.column_config.TextColumn("Segment", width="medium"),
        "Kullanıcı Sayısı":   st.column_config.NumberColumn("Kullanıcı", format="%d"),
        "Ort. Recency (Gün)": st.column_config.NumberColumn("Ort. Recency (Gün)", format="%d"),
        "Ort. Frequency":     st.column_config.NumberColumn("Ort. Frequency", format="%.1f"),
        "Ort. Monetary":      st.column_config.NumberColumn("Ort. Monetary", format="%d"),
        "Kampanya Önerisi":   st.column_config.TextColumn("Kampanya Önerisi", width="large"),
    },
)

st.divider()

# ─── Detay RFM tablosu ────────────────────────────────────────────────────────

st.subheader("🔍 Kullanıcı RFM Detay Tablosu")

if table_df.empty:
    st.info("Tablo için veri yok.")
else:
    display_df = table_df.copy()
    if seg_filter != "Tümü":
        display_df = display_df[display_df["Segment"] == seg_filter]

    col_search, col_info = st.columns([3, 1])
    with col_search:
        search_text = st.text_input("Şehir veya profil ara", placeholder="örn. İstanbul")
    with col_info:
        st.metric("Gösterilen Kayıt", len(display_df))

    if search_text:
        mask = (
            display_df["Şehir"].str.contains(search_text, case=False, na=False)
            | display_df["Profil"].str.contains(search_text, case=False, na=False)
        )
        display_df = display_df[mask]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Kullanıcı ID":  st.column_config.NumberColumn("ID",      format="%d"),
            "Recency (Gün)": st.column_config.NumberColumn("Recency", format="%d"),
            "Frequency":     st.column_config.NumberColumn("Frequency", format="%d"),
            "Monetary":      st.column_config.NumberColumn("Monetary",  format="%d"),
            "R":             st.column_config.NumberColumn("R", format="%d"),
            "F":             st.column_config.NumberColumn("F", format="%d"),
            "M":             st.column_config.NumberColumn("M", format="%d"),
        },
    )
