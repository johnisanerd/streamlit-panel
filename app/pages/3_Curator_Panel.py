"""
Küratör Paneli — küratörlerin otel önerilerini sisteme eklediği yönetim ekranı.

Özellikler:
  - Küratör seçimi veya yeni küratör ekleme
  - Otel seçimi (hotels tablosundan)
  - Instagram post URL, küratör notu, kategori, serbest etiket, skor
  - curators + curated_hotels tablolarına kayıt
  - Mevcut önerilerin tablosu
  - Instagram scraping bu sprintte yok — sadece manuel giriş
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.crm.models import CuratedHotel, Curator, Hotel
from src.database.db import Base, engine, get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Sabitler ─────────────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "romantik kaçamak",
    "aile tatili",
    "lüks deneyim",
    "butik otel",
    "gastronomi",
    "doğa tatili",
    "spa & wellness",
    "iş seyahati",
]

_SCORE_LABELS = {
    1: "⭐ Zayıf",   2: "⭐⭐ Orta-altı", 3: "⭐⭐⭐ Orta",
    4: "⭐⭐⭐⭐ İyi", 5: "⭐⭐⭐⭐⭐ Mükemmel",
}


# ─── Tablo kurulumu ───────────────────────────────────────────────────────────

def _ensure_tables() -> None:
    """curators ve curated_hotels tablolarının var olduğunu garantiler."""
    import src.crm.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


# ─── Veri yükleme ─────────────────────────────────────────────────────────────

def _load_curators() -> list[tuple[int, str]]:
    """(id, görünüm_adı) listesi — selectbox için. Session'da cache'lenir."""
    if "curator_index" in st.session_state:
        return st.session_state["curator_index"]
    try:
        with get_db() as db:
            rows = (
                db.query(Curator.id, Curator.name, Curator.instagram_username)
                .filter(Curator.is_active == True)
                .order_by(Curator.name)
                .all()
            )
            index = [
                (r.id, f"{r.name}" + (f"  (@{r.instagram_username})" if r.instagram_username else ""))
                for r in rows
            ]
        st.session_state["curator_index"] = index
        return index
    except Exception as exc:
        logger.error("Küratör listesi yüklenemedi: %s", exc)
        return []


def _load_hotels_index() -> list[tuple[int, str]]:
    """(id, 'Otel Adı — Şehir') listesi — selectbox için."""
    if "hotel_index_curator" in st.session_state:
        return st.session_state["hotel_index_curator"]
    try:
        with get_db() as db:
            rows = (
                db.query(Hotel.id, Hotel.name, Hotel.city)
                .filter(Hotel.is_active == True)
                .order_by(Hotel.city, Hotel.name)
                .all()
            )
            index = [(r.id, f"{r.name}  —  {r.city}") for r in rows]
        st.session_state["hotel_index_curator"] = index
        return index
    except Exception as exc:
        logger.error("Otel listesi yüklenemedi: %s", exc)
        return []


def _load_curated_table() -> pd.DataFrame:
    """Tüm curated_hotels kayıtlarını DataFrame olarak döndürür."""
    try:
        with get_db() as db:
            rows = (
                db.query(
                    CuratedHotel.id,
                    Curator.name.label("küratör"),
                    Hotel.name.label("otel"),
                    Hotel.city.label("şehir"),
                    CuratedHotel.categories,
                    CuratedHotel.tags,
                    CuratedHotel.score,
                    CuratedHotel.source_post_url,
                    CuratedHotel.curator_note,
                    CuratedHotel.created_at,
                )
                .join(Curator, CuratedHotel.curator_id == Curator.id)
                .join(Hotel,   CuratedHotel.hotel_id   == Hotel.id)
                .order_by(CuratedHotel.created_at.desc())
                .all()
            )

        if not rows:
            return pd.DataFrame()

        records = []
        for r in rows:
            cats = json.loads(r.categories or "[]")
            tags = json.loads(r.tags or "[]")
            records.append({
                "ID":           r.id,
                "Küratör":      r.küratör,
                "Otel":         r.otel,
                "Şehir":        r.şehir,
                "Kategoriler":  ", ".join(cats),
                "Etiketler":    ", ".join(tags),
                "Skor":         f"{r.score:.1f} / 10",
                "Instagram":    r.source_post_url or "—",
                "Not":          (r.curator_note or "")[:80] + ("…" if r.curator_note and len(r.curator_note) > 80 else ""),
                "Tarih":        r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
            })
        return pd.DataFrame(records)
    except Exception as exc:
        logger.error("Curated hotels tablosu yüklenemedi: %s", exc)
        return pd.DataFrame()


# ─── Kayıt işlemleri ──────────────────────────────────────────────────────────

def _save_curator(name: str, instagram: str, bio: str, niche: str, trust_score: float) -> int | None:
    """Yeni küratör kaydeder, id döndürür."""
    try:
        with get_db() as db:
            c = Curator(
                name=name.strip(),
                instagram_username=instagram.strip().lstrip("@") or None,
                bio=bio.strip() or None,
                niche=niche.strip() or None,
                trust_score=trust_score,
            )
            db.add(c)
            db.flush()
            new_id = c.id
        # Önbelleği temizle
        st.session_state.pop("curator_index", None)
        return new_id
    except Exception as exc:
        logger.error("Küratör kaydedilemedi: %s", exc)
        st.error(f"Küratör kaydedilirken hata oluştu: {exc}")
        return None


def _save_curated_hotel(
    curator_id:   int,
    hotel_id:     int,
    post_url:     str,
    note:         str,
    categories:   list[str],
    tags:         list[str],
    score:        float,
) -> bool:
    """Otel önerisini kaydeder. True = başarılı."""
    try:
        with get_db() as db:
            ch = CuratedHotel(
                curator_id=curator_id,
                hotel_id=hotel_id,
                source_post_url=post_url.strip() or None,
                curator_note=note.strip() or None,
                categories=json.dumps(categories, ensure_ascii=False),
                tags=json.dumps(tags, ensure_ascii=False),
                score=score,
            )
            db.add(ch)
        return True
    except Exception as exc:
        logger.error("Otel önerisi kaydedilemedi: %s", exc)
        st.error(f"Kayıt sırasında hata oluştu: {exc}")
        return False


# ─── Sidebar: küratör istatistikleri ─────────────────────────────────────────

def _render_sidebar_stats() -> None:
    with st.sidebar:
        st.header("📊 Hızlı İstatistikler")
        try:
            with get_db() as db:
                n_curators = db.query(Curator).filter(Curator.is_active == True).count()
                n_curated  = db.query(CuratedHotel).count()
            st.metric("Aktif Küratör", n_curators)
            st.metric("Toplam Öneri",  n_curated)
        except Exception:
            st.caption("İstatistik yüklenemedi.")
        st.divider()
        st.page_link("pages/1_Discovery.py",   label="← Keşfe Dön",    icon="🔍")
        st.page_link("pages/2_Hotel_Detail.py", label="← Otel Detay",  icon="🏨")


# ─── Tab 1: Otel önerisi ekle ─────────────────────────────────────────────────

def _tab_add_recommendation() -> None:
    """Küratör otel önerisi ekleme formu."""

    curator_index = _load_curators()
    hotel_index   = _load_hotels_index()

    if not hotel_index:
        st.warning("⚠️ Otel bulunamadı. Lütfen önce sentetik veri oluşturun.")
        st.code("python scripts/generate_synthetic_data.py --reset", language="bash")
        return

    # ── Küratör seçimi ────────────────────────────────────────────────────────
    st.subheader("1️⃣ Küratör")

    curator_col, new_col = st.columns([3, 1])

    with curator_col:
        if curator_index:
            c_names    = [name for _, name in curator_index]
            c_ids      = [cid  for cid,  _ in curator_index]
            chosen_c   = st.selectbox("Mevcut küratör seç", c_names, key="sel_curator")
            selected_curator_id = c_ids[c_names.index(chosen_c)]
        else:
            st.info("Henüz küratör yok. Sağdaki formu kullanarak ilk küratörü ekleyin.")
            selected_curator_id = None

    with new_col:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        add_new = st.toggle("➕ Yeni Küratör", key="toggle_new_curator")

    if add_new:
        with st.container(border=True):
            st.markdown("**Yeni Küratör Ekle**")
            nc1, nc2 = st.columns(2)
            new_name  = nc1.text_input("Ad Soyad *", key="new_c_name")
            new_ig    = nc2.text_input("Instagram Kullanıcı Adı", placeholder="@kullanici", key="new_c_ig")
            new_niche = st.selectbox("Uzmanlık Alanı", [""] + CATEGORIES, key="new_c_niche",
                                     format_func=lambda x: "— Seçiniz —" if x == "" else x)
            new_bio   = st.text_area("Biyografi", key="new_c_bio", height=80)
            new_trust = st.slider("Güven Skoru", 1.0, 10.0, 7.0, 0.5, key="new_c_trust")

            if st.button("💾 Küratörü Kaydet", key="btn_save_curator"):
                if not new_name.strip():
                    st.error("Ad alanı zorunludur.")
                else:
                    new_id = _save_curator(new_name, new_ig, new_bio, new_niche, new_trust)
                    if new_id:
                        st.success(f"✅ Küratör eklendi (id={new_id}). Lütfen sayfayı yenileyerek seçin.")
                        # Toggle'ı kapat
                        st.session_state["toggle_new_curator"] = False
                        st.rerun()

    if selected_curator_id is None:
        st.stop()

    st.divider()

    # ── Otel seçimi ───────────────────────────────────────────────────────────
    st.subheader("2️⃣ Otel")
    h_names = [name for _, name in hotel_index]
    h_ids   = [hid  for hid,  _ in hotel_index]
    chosen_h = st.selectbox("Önerilecek oteli seç", h_names, key="sel_hotel")
    selected_hotel_id = h_ids[h_names.index(chosen_h)]

    st.divider()

    # ── Öneri detayları ───────────────────────────────────────────────────────
    st.subheader("3️⃣ Öneri Detayları")

    with st.form("curated_hotel_form", clear_on_submit=True):
        post_url = st.text_input(
            "Instagram Post URL",
            placeholder="https://www.instagram.com/p/xxxxx/",
            help="Opsiyonel — Instagram scraping bu sprintte aktif değil.",
        )

        note = st.text_area(
            "Küratör Notu *",
            placeholder="Bu oteli neden öneriyorsunuz? Öne çıkan özellikleri neler?",
            height=120,
        )

        selected_cats = st.multiselect(
            "Kategoriler",
            CATEGORIES,
            help="Birden fazla kategori seçebilirsiniz.",
        )

        raw_tags = st.text_input(
            "Serbest Etiketler",
            placeholder="örn: gün batımı manzarası, rooftop bar, infinity pool",
            help="Virgülle ayırarak yazın.",
        )

        score = st.slider(
            "Küratör Skoru",
            min_value=1.0,
            max_value=10.0,
            value=7.5,
            step=0.5,
            format="%.1f",
            help="Bu otele verdiğiniz genel puan (1–10).",
        )
        score_label = _SCORE_LABELS.get(round(score / 2), "")
        st.caption(f"Seçilen skor: **{score:.1f} / 10**  {score_label}")

        submitted = st.form_submit_button("💾 Öneriyi Kaydet", use_container_width=True, type="primary")

    if submitted:
        if not note.strip():
            st.error("Küratör notu zorunludur.")
        else:
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
            ok = _save_curated_hotel(
                curator_id=selected_curator_id,
                hotel_id=selected_hotel_id,
                post_url=post_url,
                note=note,
                categories=selected_cats,
                tags=tags_list,
                score=score,
            )
            if ok:
                st.success("✅ Otel önerisi başarıyla kaydedildi!")
                st.balloons()
                # Tablo cache'ini temizle
                st.session_state.pop("curated_table_cache", None)


# ─── Tab 2: Mevcut öneriler ───────────────────────────────────────────────────

def _tab_view_recommendations() -> None:
    """Mevcut küratör önerilerini tablo olarak gösterir."""

    col_refresh, col_info = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Yenile", use_container_width=True):
            st.session_state.pop("curated_table_cache", None)

    df = _load_curated_table()

    if df.empty:
        st.info('Henüz kayıtlı öneri yok. "Otel Önerisi Ekle" sekmesinden başlayın.')
        return

    # Filtre
    col_filter, col_sort = st.columns([3, 1])
    with col_filter:
        filter_text = st.text_input("Ara", placeholder="Küratör, otel veya şehir...", label_visibility="collapsed")
    with col_sort:
        sort_col = st.selectbox("Sırala", ["Tarih ↓", "Skor ↓", "Küratör ↑"], label_visibility="collapsed")

    if filter_text:
        mask = df.apply(lambda row: filter_text.lower() in row.to_string().lower(), axis=1)
        df = df[mask]

    if sort_col == "Skor ↓":
        df = df.sort_values("Skor", ascending=False)
    elif sort_col == "Küratör ↑":
        df = df.sort_values("Küratör")

    st.markdown(f"**{len(df)} öneri**")
    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Instagram": st.column_config.LinkColumn("Instagram", display_text="Göster"),
        },
    )


# ─── Tab 3: Küratör listesi ───────────────────────────────────────────────────

def _tab_view_curators() -> None:
    """Kayıtlı küratörleri tablo olarak gösterir."""
    try:
        with get_db() as db:
            rows = db.query(Curator).filter(Curator.is_active == True).order_by(Curator.name).all()
            if not rows:
                st.info("Henüz küratör kayıtlı değil.")
                return
            records = [
                {
                    "Küratör":          r.name,
                    "Instagram":        f"@{r.instagram_username}" if r.instagram_username else "—",
                    "Uzmanlık":         r.niche or "—",
                    "Güven Skoru":      f"{r.trust_score:.1f} / 10",
                    "Biyografi":        (r.bio or "")[:80] + ("…" if r.bio and len(r.bio) > 80 else ""),
                    "Kayıt Tarihi":     r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
                }
                for r in rows
            ]
        df = pd.DataFrame(records)
        st.markdown(f"**{len(df)} aktif küratör**")
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as exc:
        logger.error("Küratör tablosu yüklenemedi: %s", exc)
        st.error("Küratörler yüklenirken hata oluştu.")


# ─── Sayfa giriş noktası ──────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Küratör Paneli | SuggesMe",
        page_icon="✍️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Tabloların var olduğunu garantile (yeni tablolar)
    _ensure_tables()

    _render_sidebar_stats()

    st.title("✍️ Küratör Paneli")
    st.caption("Otel önerilerini manuel olarak ekleyin ve mevcut önerileri yönetin.")

    tab1, tab2, tab3 = st.tabs([
        "➕ Otel Önerisi Ekle",
        "📋 Mevcut Öneriler",
        "👤 Küratörler",
    ])

    with tab1:
        _tab_add_recommendation()

    with tab2:
        _tab_view_recommendations()

    with tab3:
        _tab_view_curators()


main()
