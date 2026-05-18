"""
Streamlit sayfaları için ortak yardımcı fonksiyonlar.
Demo kullanıcı yönetimi ve event tracking burada merkezi tutulur.
"""

import json
import uuid
from datetime import datetime

import streamlit as st

from src.crm.models import CRMUser, UserEvent
from src.database.db import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_or_create_demo_user() -> int:
    """
    Tarayıcı session'ı boyunca sabit bir demo kullanıcı id'si döndürür.
    İlk çağrıda crm_users tablosuna yeni kayıt ekler.
    """
    if "demo_user_id" in st.session_state:
        return st.session_state["demo_user_id"]

    try:
        sid = str(uuid.uuid4())
        with get_db() as db:
            user = CRMUser(
                session_id=sid,
                profile_type="budget_traveler",
                preferred_budget="mid",
                travel_type="general",
                age_range="25-34",
                device_type="web",
                city="Demo",
            )
            db.add(user)
            db.flush()
            uid = user.id
        st.session_state["demo_user_id"]    = uid
        st.session_state["demo_session_id"] = sid
        logger.debug("Demo kullanıcı oluşturuldu: id=%d", uid)
        return uid
    except Exception as exc:
        logger.error("Demo kullanıcı oluşturulamadı: %s", exc)
        return -1


def track_event(
    user_id:    int,
    hotel_id:   int | None,
    event_type: str,
    meta:       dict | None = None,
) -> None:
    """
    user_events tablosuna olay kaydeder.
    Hata oluşursa sessizce loglanır; UI akışı kesilmez.
    """
    if user_id < 0:
        return
    try:
        with get_db() as db:
            db.add(UserEvent(
                user_id=user_id,
                hotel_id=hotel_id,
                event_type=event_type,
                event_date=datetime.now(),
                session_id=st.session_state.get("demo_session_id"),
                source="web",
                metadata_json=json.dumps(meta, ensure_ascii=False) if meta else None,
            ))
    except Exception as exc:
        logger.error("Event tracking hatası [%s]: %s", event_type, exc)
