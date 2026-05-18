"""
Kampanya Otomasyon Paneli — Sprint 8

RFM segmentlerine göre n8n webhook kampanya simülasyonu.
Gerçek mesaj gönderilmez; sadece webhook tetiklenir (veya demo modda ekranda gösterilir).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

import pandas as pd
import streamlit as st
from sqlalchemy import func

from src.automation.n8n_client import (
    CAMPAIGN_TYPES,
    CHANNELS,
    SEGMENT_MESSAGES,
    build_payload,
    ensure_tables,
    get_campaign_history,
    is_webhook_configured,
    save_automation_event,
    send_webhook,
)
from src.crm.models import Hotel, RFMScore
from src.crm.rfm_analysis import SEGMENT_ORDER
from src.database.db import get_db

st.set_page_config(
    page_title="Kampanya Otomasyonu — SuggesMe",
    page_icon="📣",
    layout="wide",
)

ensure_tables()

# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def _load_hotels() -> list[dict]:
    if "camp_hotel_index" not in st.session_state:
        try:
            with get_db() as db:
                hotels = (
                    db.query(Hotel.id, Hotel.name, Hotel.city)
                    .filter(Hotel.is_active == True)
                    .order_by(Hotel.name)
                    .all()
                )
                st.session_state["camp_hotel_index"] = [
                    {"id": h.id, "name": h.name, "city": h.city}
                    for h in hotels
                ]
        except Exception as exc:
            st.error(f"Otel listesi yüklenemedi: {exc}")
            st.session_state["camp_hotel_index"] = []
    return st.session_state["camp_hotel_index"]


def _get_segment_counts() -> dict[str, int]:
    """rfm_scores tablosundan segment bazlı kullanıcı sayılarını döndürür."""
    if "camp_seg_counts" not in st.session_state:
        try:
            with get_db() as db:
                rows = (
                    db.query(RFMScore.rfm_segment, func.count(RFMScore.id))
                    .group_by(RFMScore.rfm_segment)
                    .all()
                )
            st.session_state["camp_seg_counts"] = {r[0]: r[1] for r in rows}
        except Exception:
            st.session_state["camp_seg_counts"] = {}
    return st.session_state["camp_seg_counts"]


# ─── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("📣 Kampanya Otomasyonu")

hotels = _load_hotels()
if not hotels:
    st.sidebar.warning("Aktif otel bulunamadı.")
    st.stop()

hotel_options = {h["id"]: f"{h['name']} ({h['city']})" for h in hotels}
selected_hotel_id = st.sidebar.selectbox(
    "Otel seçin",
    options=list(hotel_options.keys()),
    format_func=lambda hid: hotel_options[hid],
    key="camp_hotel_id",
)
selected_hotel_name = next(h["name"] for h in hotels if h["id"] == selected_hotel_id)

st.sidebar.divider()

if is_webhook_configured():
    st.sidebar.success("n8n webhook bağlı")
else:
    st.sidebar.warning("n8n webhook tanımlı değil — **Demo Mod**")
    st.sidebar.caption("Payload ekranda gösterilir, gerçek istek yapılmaz.")

st.sidebar.divider()
st.sidebar.page_link("streamlit_app.py",            label="← Ana Sayfa",     icon="🏠")
st.sidebar.page_link("pages/4_Business_Panel.py",   label="İşletme Paneli",  icon="📊")
st.sidebar.page_link("pages/5_CRM_RFM_Analytics.py", label="RFM Analizi",    icon="🎯")

# ─── Başlık ───────────────────────────────────────────────────────────────────

st.title("📣 Kampanya Otomasyon Paneli")
st.caption(
    "RFM segmentine göre hedef kitleyi belirleyin, mesajı özelleştirin "
    "ve n8n üzerinden webhook kampanyası tetikleyin."
)

seg_counts = _get_segment_counts()

if not seg_counts:
    st.info(
        "RFM verisi bulunamadı. Önce **RFM Analizi** sayfasından analiz çalıştırın. "
        "Analiz olmadan da kampanya gönderebilirsiniz, ancak hedef kitle sayısı 0 görünür."
    )

st.divider()

# ─── Kampanya Formu ───────────────────────────────────────────────────────────

st.subheader("🎯 Kampanya Oluştur")

col_form, col_preview = st.columns([3, 2])

with col_form:
    # Segment
    seg_labels = []
    for s in SEGMENT_ORDER:
        count = seg_counts.get(s, 0)
        seg_labels.append(f"{s} ({count} kullanıcı)")

    seg_idx = st.selectbox(
        "Hedef Segment",
        options=range(len(SEGMENT_ORDER)),
        format_func=lambda i: seg_labels[i],
        key="camp_segment_idx",
    )
    selected_segment = SEGMENT_ORDER[seg_idx]
    target_count = seg_counts.get(selected_segment, 0)

    # Kanal
    channel = st.selectbox("Kanal", CHANNELS, key="camp_channel")

    # Kampanya tipi
    campaign_type = st.selectbox("Kampanya Tipi", CAMPAIGN_TYPES, key="camp_type")

    # Kampanya adı (otomatik, düzenlenebilir)
    default_name = f"{campaign_type} — {selected_hotel_name} ({selected_segment})"
    campaign_name = st.text_input("Kampanya Adı", value=default_name, key="camp_name")

    # Mesaj şablonu (segment'e göre otomatik, düzenlenebilir)
    default_msg = SEGMENT_MESSAGES.get(selected_segment, "").format(hotel_name=selected_hotel_name)
    message = st.text_area(
        "Mesaj Şablonu",
        value=default_msg,
        height=120,
        key=f"camp_msg_{selected_segment}",
        help="Mesajı ihtiyacınıza göre düzenleyebilirsiniz.",
    )

    send_btn = st.button(
        "🚀 Test Webhook Gönder",
        type="primary",
        use_container_width=True,
        disabled=not campaign_name.strip() or not message.strip(),
    )

with col_preview:
    st.markdown("**Payload Önizlemesi**")
    preview_payload = build_payload(
        campaign_name=campaign_name or default_name,
        hotel_name=selected_hotel_name,
        segment=selected_segment,
        channel=channel,
        campaign_type=campaign_type,
        message=message or default_msg,
        target_user_count=target_count,
    )
    st.json(preview_payload)

# ─── Gönderim ─────────────────────────────────────────────────────────────────

if send_btn:
    payload = build_payload(
        campaign_name=campaign_name,
        hotel_name=selected_hotel_name,
        segment=selected_segment,
        channel=channel,
        campaign_type=campaign_type,
        message=message,
        target_user_count=target_count,
    )

    with st.spinner("Webhook gönderiliyor…"):
        result = send_webhook(payload)

    saved = save_automation_event(
        hotel_id=selected_hotel_id,
        payload=payload,
        webhook_result=result,
    )

    # Geçmiş önbelleğini sıfırla
    st.session_state.pop("camp_history", None)

    # Sonuç göster
    if result["mode"] == "demo":
        st.success("Demo Mod — Webhook simüle edildi ve kaydedildi.")
        st.markdown("**Gönderilecek payload:**")
        st.json(payload)
    elif result["status"] == "sent":
        st.success(f"Webhook başarıyla gönderildi (HTTP {result.get('status_code', '?')}).")
    else:
        st.error(f"Webhook gönderilemedi: {result.get('error', 'Bilinmeyen hata')}")

    if not saved:
        st.warning("Kampanya veritabanına kaydedilemedi.")

st.divider()

# ─── Kampanya Geçmişi ─────────────────────────────────────────────────────────

st.subheader("📋 Kampanya Geçmişi")

if "camp_history" not in st.session_state:
    st.session_state["camp_history"] = get_campaign_history(limit=20)

history = st.session_state["camp_history"]

if not history:
    st.info("Henüz gönderilmiş kampanya yok. Yukarıdaki formu kullanarak ilk kampanyanızı oluşturun.")
else:
    df_hist = pd.DataFrame(history).rename(columns={
        "id":                 "ID",
        "hotel_name":         "Otel",
        "campaign_name":      "Kampanya Adı",
        "segment":            "Segment",
        "channel":            "Kanal",
        "campaign_type":      "Kampanya Tipi",
        "target_user_count":  "Hedef Kullanıcı",
        "webhook_status":     "Durum",
        "created_at":         "Tarih",
    })

    STATUS_EMOJI = {"simulated": "🟡 Demo", "sent": "🟢 Gönderildi", "failed": "🔴 Hata"}
    df_hist["Durum"] = df_hist["Durum"].map(lambda s: STATUS_EMOJI.get(s, s))

    st.dataframe(
        df_hist[["ID", "Otel", "Kampanya Adı", "Segment", "Kanal",
                 "Kampanya Tipi", "Hedef Kullanıcı", "Durum", "Tarih"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID":              st.column_config.NumberColumn("ID",    format="%d"),
            "Hedef Kullanıcı": st.column_config.NumberColumn("Hedef", format="%d"),
            "Tarih":           st.column_config.DatetimeColumn("Tarih", format="DD.MM.YYYY HH:mm"),
        },
    )
