"""
Öneri ve Kümeleme Paneli — Sprint 11

Kullanıcı profiline göre kişiselleştirilmiş otel önerileri (cosine similarity)
ve otel segmentasyonu (KMeans kümeleme) gösterir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.express as px
import streamlit as st

from src.recommendation.clustering import cluster_hotels, get_cluster_summary
from src.recommendation.recommender import (
    PROFILE_TAGS,
    PROFILE_TR,
    find_similar_hotels,
    load_hotels_df,
    recommend_for_profile,
)

st.set_page_config(
    page_title="Öneri Sistemi — SuggesMe",
    page_icon="🤖",
    layout="wide",
)

# ─── Yardımcılar ──────────────────────────────────────────────────────────────

PRICE_BADGE = {"budget": "🟢 Ekonomik", "mid": "🟡 Orta", "luxury": "🔴 Lüks"}
STAR_STR    = {3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}


def _hotel_card(row: dict, show_similarity: bool = True) -> None:
    with st.container(border=True):
        col_info, col_score = st.columns([4, 1])
        with col_info:
            stars_str = STAR_STR.get(int(row.get("stars") or 4), "⭐⭐⭐⭐")
            st.markdown(f"**{row['name']}** {stars_str}")
            st.caption(f"📍 {row.get('city', '')} / {row.get('district', '')}")

            price_lbl = PRICE_BADGE.get(row.get("price_level", "mid"), "")
            rating    = row.get("rating") or 0
            reviews   = row.get("review_count") or 0
            st.caption(f"{price_lbl}  ·  ⭐ {rating:.1f} ({reviews} yorum)")

            tags = row.get("profile_tags") or []
            if tags:
                tag_str = "  ·  ".join(PROFILE_TR.get(t, t) for t in tags[:3])
                st.caption(tag_str)

        with col_score:
            if show_similarity:
                sim = row.get("similarity_pct", 0)
                color = "green" if sim >= 80 else ("orange" if sim >= 60 else "gray")
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span style='font-size:1.3em;font-weight:bold;color:{color}'>"
                    f"%{sim:.0f}</span><br><small>eşleşme</small></div>",
                    unsafe_allow_html=True,
                )


def _get_cities() -> list[str]:
    df = load_hotels_df()
    if df.empty:
        return []
    return sorted(df["city"].unique().tolist())


# ─── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("🤖 Öneri Sistemi")
st.sidebar.caption("Cosine similarity + KMeans kümeleme")

st.sidebar.subheader("Kullanıcı Profili")

profile_options = list(PROFILE_TR.keys())
profile_labels  = [PROFILE_TR[p] for p in profile_options]
profile_idx = st.sidebar.selectbox(
    "Profil Tipi",
    options=range(len(profile_options)),
    format_func=lambda i: profile_labels[i],
    key="rec_profile_idx",
)
selected_profile = profile_options[profile_idx]

budget_map = {"budget": "💰 Ekonomik", "mid": "🟡 Orta", "luxury": "💎 Lüks"}
selected_budget = st.sidebar.selectbox(
    "Bütçe",
    options=list(budget_map.keys()),
    format_func=lambda k: budget_map[k],
    index=1,
    key="rec_budget",
)

cities = ["Tüm Şehirler"] + _get_cities()
selected_city = st.sidebar.selectbox("Şehir", cities, key="rec_city")

top_n = st.sidebar.slider("Öneri sayısı", 3, 12, 6)

st.sidebar.divider()
st.sidebar.page_link("streamlit_app.py",          label="← Ana Sayfa",     icon="🏠")
st.sidebar.page_link("pages/1_Discovery.py",       label="Otel Keşfet",     icon="🔍")
st.sidebar.page_link("pages/4_Business_Panel.py",  label="İşletme Paneli",  icon="📊")

# ─── Başlık ───────────────────────────────────────────────────────────────────

st.title("🤖 Öneri ve Kümeleme Sistemi")
st.caption(
    "Cosine similarity ile profil bazlı öneriler · KMeans ile otel segmentasyonu. "
    "Model tamamen sentetik verilerle çalışır ve açıklanabilir."
)

tab_rec, tab_cluster, tab_similar = st.tabs(
    ["🎯 Kişiselleştirilmiş Öneriler", "🗂️ Küme Analizi", "🔗 Benzer Oteller"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Kişiselleştirilmiş öneriler
# ══════════════════════════════════════════════════════════════════════════════
with tab_rec:
    st.subheader(
        f"{PROFILE_TR[selected_profile]} profili için öneriler "
        f"— {budget_map[selected_budget]}"
    )

    cache_key = f"rec_{selected_profile}_{selected_budget}_{selected_city}_{top_n}"
    if cache_key not in st.session_state:
        city_filter = None if selected_city == "Tüm Şehirler" else selected_city
        with st.spinner("Öneriler hesaplanıyor…"):
            st.session_state[cache_key] = recommend_for_profile(
                profile_type=selected_profile,
                preferred_budget=selected_budget,
                city=city_filter,
                top_n=top_n,
            )

    rec_df = st.session_state[cache_key]

    if rec_df.empty:
        st.warning("Seçilen kriterlere uygun otel bulunamadı.")
    else:
        st.caption(f"{len(rec_df)} otel bulundu — özellik benzerliğine göre sıralandı.")

        # Otel kartları (3'lü grid)
        cols_per_row = 3
        rows = [rec_df.iloc[i:i + cols_per_row] for i in range(0, len(rec_df), cols_per_row)]
        for row_df in rows:
            cols = st.columns(cols_per_row)
            for col, (_, hotel) in zip(cols, row_df.iterrows()):
                with col:
                    _hotel_card(hotel.to_dict(), show_similarity=True)

        # Similarity chart
        st.divider()
        fig = px.bar(
            rec_df,
            x="name",
            y="similarity_pct",
            color="price_level",
            text="similarity_pct",
            title="Profil Eşleşme Oranı (%)",
            labels={"name": "Otel", "similarity_pct": "Eşleşme (%)", "price_level": "Fiyat"},
            color_discrete_map={"budget": "#2ECC71", "mid": "#F39C12", "luxury": "#E74C3C"},
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="", showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Küme analizi
# ══════════════════════════════════════════════════════════════════════════════
with tab_cluster:
    st.subheader("Otel Segmentasyonu — KMeans Kümeleme")

    col_k, col_btn = st.columns([2, 3])
    n_clusters = col_k.slider("Küme sayısı", 2, 8, 5, key="n_clusters")
    run_cluster = col_btn.button("▶️ Kümeleri Hesapla", type="primary", use_container_width=True)

    cluster_cache_key = f"cluster_{n_clusters}"
    if run_cluster or cluster_cache_key not in st.session_state:
        with st.spinner("KMeans çalışıyor…"):
            cluster_df  = cluster_hotels(n_clusters=n_clusters)
            summary_df  = get_cluster_summary(cluster_df)
            st.session_state[cluster_cache_key] = (cluster_df, summary_df)

    if cluster_cache_key in st.session_state:
        cluster_df, summary_df = st.session_state[cluster_cache_key]

        if cluster_df.empty:
            st.warning("Kümeleme için yeterli veri yok.")
        else:
            # KPI
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Otel",    len(cluster_df))
            col2.metric("Küme Sayısı",    cluster_df["cluster_id"].nunique())
            col3.metric("Özellik Boyutu", "9 (price + rating + stars + 6 tag)")

            st.divider()

            # Küme dağılımı grafiği
            col_pie, col_bar = st.columns(2)
            with col_pie:
                fig_pie = px.pie(
                    cluster_df,
                    names="cluster_name",
                    title="Küme Dağılımı (Otel Sayısı)",
                    hole=0.3,
                )
                fig_pie.update_traces(textinfo="percent+label")
                fig_pie.update_layout(showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_bar:
                fig_bar = px.bar(
                    summary_df,
                    x="Küme Adı",
                    y="Otel Sayısı",
                    color="Fiyat Segmenti",
                    text="Otel Sayısı",
                    title="Küme Başına Otel Sayısı",
                    color_discrete_map={
                        "Ekonomik": "#2ECC71",
                        "Orta":     "#F39C12",
                        "Lüks":     "#E74C3C",
                    },
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(xaxis_title="", showlegend=True)
                st.plotly_chart(fig_bar, use_container_width=True)

            # Küme özet tablosu
            st.subheader("Küme Özeti")
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ort. Rating": st.column_config.NumberColumn("Ort. Rating", format="%.2f"),
                },
            )

            # Tüm otel-küme tablosu
            st.subheader("Otel — Küme Ataması")

            # Küme filtresi
            all_cluster_names = ["Tümü"] + cluster_df["cluster_name"].unique().tolist()
            cluster_filter = st.selectbox("Küme filtrele", all_cluster_names, key="cluster_filter")

            disp_df = cluster_df.copy()
            if cluster_filter != "Tümü":
                disp_df = disp_df[disp_df["cluster_name"] == cluster_filter]

            disp_df["Profil Etiketleri"] = disp_df["profile_tags"].apply(
                lambda tags: ", ".join(PROFILE_TR.get(t, t) for t in (tags or [])[:3])
            )

            st.dataframe(
                disp_df.rename(columns={
                    "name":         "Otel",
                    "city":         "Şehir",
                    "price_level":  "Fiyat",
                    "rating":       "Rating",
                    "stars":        "Yıldız",
                    "cluster_name": "Küme",
                })[["Otel", "Şehir", "Fiyat", "Rating", "Yıldız",
                    "Profil Etiketleri", "Küme"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rating":  st.column_config.NumberColumn("Rating", format="%.1f"),
                    "Yıldız":  st.column_config.NumberColumn("Yıldız", format="%d"),
                },
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Benzer oteller
# ══════════════════════════════════════════════════════════════════════════════
with tab_similar:
    st.subheader("Benzer Otel Bulucu")
    st.caption("Bir otel seçin; cosine similarity ile en benzer 4 oteli görün.")

    hotels_df = load_hotels_df()
    if hotels_df.empty:
        st.warning("Otel verisi bulunamadı.")
    else:
        hotel_options_map = {
            row["hotel_id"]: f"{row['name']} ({row['city']})"
            for _, row in hotels_df.iterrows()
        }
        selected_hotel_id = st.selectbox(
            "Referans Otel",
            options=list(hotel_options_map.keys()),
            format_func=lambda hid: hotel_options_map[hid],
            key="sim_hotel_id",
        )

        sim_cache_key = f"sim_{selected_hotel_id}"
        if sim_cache_key not in st.session_state:
            st.session_state[sim_cache_key] = find_similar_hotels(selected_hotel_id, top_n=4)

        sim_df = st.session_state[sim_cache_key]

        if sim_df.empty:
            st.info("Yeterli otel verisi yok.")
        else:
            ref_hotel = hotels_df[hotels_df["hotel_id"] == selected_hotel_id].iloc[0]
            st.markdown("**Seçilen Otel:**")
            _hotel_card(ref_hotel.to_dict(), show_similarity=False)

            st.markdown("**Benzer Oteller:**")
            cols = st.columns(len(sim_df))
            for col, (_, hotel) in zip(cols, sim_df.iterrows()):
                with col:
                    _hotel_card(hotel.to_dict(), show_similarity=True)

        if st.button("🔄 Yenile", key="sim_refresh"):
            st.session_state.pop(sim_cache_key, None)
            st.rerun()
