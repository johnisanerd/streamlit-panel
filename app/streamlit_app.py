"""
SuggesMe ana Streamlit uygulaması.
Kullanıcıları uygun sayfalara yönlendiren anasayfa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.utils.config import config

st.set_page_config(
    page_title="SuggesMe",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💡 SuggesMe")
st.caption("Küratörlük tabanlı otel keşif ve işletme CRM analitiği platformu.")

st.write("")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🏨 Otel Keşfet")
        st.write("Küratörler tarafından seçilmiş otelleri filtreleyin ve en uygununu bulun.")
        st.page_link("pages/1_Discovery.py", label="→ Keşfe Git", icon="🔍")
        st.page_link("pages/2_Hotel_Detail.py", label="→ Otel Detay", icon="🏨")

with col2:
    with st.container(border=True):
        st.subheader("✍️ Küratör Paneli")
        st.write("Otel önerilerini sisteme ekleyin, küratörleri yönetin.")
        st.page_link("pages/3_Curator_Panel.py", label="→ Küratör Paneline Git", icon="✍️")

st.write("")
col3, col4 = st.columns(2)

with col3:
    with st.container(border=True):
        st.subheader("📊 İşletme Paneli")
        st.write("Otel performansını, etkileşim metriklerini ve rakip karşılaştırmasını görün.")
        st.page_link("pages/4_Business_Panel.py", label="→ İşletme Paneline Git", icon="📊")

with col4:
    with st.container(border=True):
        st.subheader("🎯 RFM Analizi")
        st.write("Kullanıcı segmentlerini analiz edin ve kampanya önerilerini görün.")
        st.page_link("pages/5_CRM_RFM_Analytics.py", label="→ RFM Analizine Git", icon="🎯")

st.write("")
col5, col6 = st.columns(2)

with col5:
    with st.container(border=True):
        st.subheader("📣 Kampanya Otomasyonu")
        st.write("RFM segmentlerine göre n8n webhook kampanyaları oluşturun ve tetikleyin.")
        st.page_link("pages/6_Campaign_Automation.py", label="→ Kampanya Paneline Git", icon="📣")

with col6:
    with st.container(border=True):
        st.subheader("🏢 İşletme Onboarding")
        st.write("Google Maps üzerinden otelinizi bulun ve platforma kaydedin.")
        st.page_link("pages/7_Business_Onboarding.py", label="→ Onboarding'e Git", icon="🏢")

st.write("")
col7, col8 = st.columns(2)

with col7:
    with st.container(border=True):
        st.subheader("📸 Instagram Zenginleştirme")
        st.write("Public Instagram verilerinden otel özelliklerini otomatik çıkarın.")
        st.page_link("pages/8_Instagram_Enrichment.py", label="→ Instagram Zenginleştirmeye Git", icon="📸")

with col8:
    with st.container(border=True):
        st.subheader("🤖 Öneri Sistemi")
        st.write("Cosine similarity ve KMeans ile kişiselleştirilmiş öneriler ve kümeleme.")
        st.page_link("pages/9_Recommendations.py", label="→ Öneri Sistemine Git", icon="🤖")

st.write("")
st.divider()

with st.expander("🛠️ Sistem Durumu"):
    st.json({
        "app_env":      config.APP_ENV,
        "debug":        config.APP_DEBUG,
        "database_url": config.DATABASE_URL,
    })
