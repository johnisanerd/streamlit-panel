"""
Gerçekçi sentetik CRM verisi üretici.

Platform bir süredir canlıymış gibi; otel, kullanıcı ve davranış
verilerini simüle eder. Veriler Türkiye otelcilik sektörünü baz alır.

Hedef sayılar (varsayılan):
    30 otel | 500 kullanıcı | 5 000 event
    hotel_view: 1 000 | reservation_click: 200
    whatsapp_click: 300 | favorite_added: 400
    Kalan 3 100: filter_used, website_redirect, campaign_click
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from src.crm.models import CRMUser, Hotel, UserEvent
from src.database.db import Base, engine, get_db
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Coğrafi sabitler ────────────────────────────────────────────────────────

CITY_DISTRICTS: dict[str, list[str]] = {
    "İstanbul":  ["Beşiktaş", "Kadıköy", "Şişli", "Beyoğlu", "Bakırköy", "Sarıyer"],
    "Antalya":   ["Lara", "Konyaaltı", "Muratpaşa"],
    "Bodrum":    ["Yalıkavak", "Türkbükü", "Bitez", "Gümbet"],
    "Marmaris":  ["İçmeler", "Armutalan", "Siteler"],
    "Fethiye":   ["Ölüdeniz", "Çalış", "Hisarönü"],
    "İzmir":     ["Alsancak", "Konak", "Karşıyaka", "Çeşme"],
    "Ankara":    ["Çankaya", "Kızılay", "Balgat"],
    "Trabzon":   ["Merkez", "Akçaabat"],
    "Nevşehir":  ["Ürgüp", "Göreme", "Avanos"],
    "Alanya":    ["Mahmutlar", "Oba", "Cikcilli"],
    "Belek":     ["Merkez", "Kadriye"],
    "Kemer":     ["Beldibi", "Göynük", "Çamyuva"],
}

# Şehir koordinat merkezleri (lat, lon)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "İstanbul": (41.015, 28.979),
    "Antalya":  (36.886, 30.701),
    "Bodrum":   (37.034, 27.430),
    "Marmaris": (36.855, 28.270),
    "Fethiye":  (36.622, 29.108),
    "İzmir":    (38.424, 27.143),
    "Ankara":   (39.920, 32.854),
    "Trabzon":  (41.002, 39.717),
    "Nevşehir": (38.624, 34.724),
    "Alanya":   (36.544, 32.002),
    "Belek":    (36.862, 31.054),
    "Kemer":    (36.607, 30.565),
}

BEACH_CITIES = {"Bodrum", "Marmaris", "Fethiye", "Antalya", "Alanya", "Belek", "Kemer"}
CITY_CENTERS = {"İstanbul", "Ankara", "İzmir", "Trabzon"}
NATURE_CITIES = {"Nevşehir", "Fethiye", "Trabzon"}

# ─── Otel adı üretme ─────────────────────────────────────────────────────────

_ADJECTIVES = [
    "Royal", "Golden", "Blue", "Elite", "Pearl", "Crystal",
    "Diamond", "Silver", "Prestige", "Exclusive", "Deluxe", "Premier",
    "Aegean", "Mediterranean", "Bosphorus", "Anatolian", "Azure", "Grand",
]

_NAME_TEMPLATES = [
    "{district} Grand Resort",
    "{city} Palace Hotel",
    "{district} Boutique & Spa",
    "Hotel {adj} {city}",
    "{adj} {city} Resort",
    "{district} Beach Hotel",
    "{city} {adj} Suites",
    "The {adj} {district}",
    "{district} Luxury Hotel",
    "{city} Thermal & Wellness",
    "{adj} Garden Hotel {city}",
    "{district} All Inclusive Resort",
]

# ─── Oda/olanaklar ───────────────────────────────────────────────────────────

_BASE_AMENITIES: dict[int, list[str]] = {
    3: ["wifi", "restaurant", "parking", "tv", "air_conditioning"],
    4: ["wifi", "restaurant", "parking", "pool", "gym", "bar", "tv", "air_conditioning"],
    5: ["wifi", "restaurant", "parking", "pool", "gym", "spa", "beach_access",
        "concierge", "room_service", "bar", "tennis", "air_conditioning", "tv"],
}

_BEACH_EXTRA  = ["water_sports", "snorkeling", "sunbed"]
_SPA_EXTRA    = ["hammam", "sauna", "yoga", "meditation"]
_FAMILY_EXTRA = ["kids_club", "playground", "animation", "baby_cot"]
_BIZ_EXTRA    = ["meeting_room", "business_center", "airport_shuttle"]
_NATURE_EXTRA = ["hiking_tours", "atv_tours", "hot_air_balloon"]

# ─── Fiyat aralıkları (USD/gece) ─────────────────────────────────────────────

_PRICE_RANGE: dict[int, tuple[float, float]] = {
    3: (25.0, 75.0),
    4: (75.0, 200.0),
    5: (180.0, 600.0),
}

_PRICE_LEVEL: dict[int, str] = {3: "budget", 4: "mid", 5: "luxury"}

# ─── Kullanıcı profilleri ─────────────────────────────────────────────────────

_PROFILE_DISTRIBUTION: dict[str, float] = {
    "luxury_traveler":  0.15,
    "family_vacation":  0.22,
    "budget_traveler":  0.20,
    "honeymoon":        0.12,
    "business_traveler":0.18,
    "wellness_spa":     0.13,
}

_PROFILE_BUDGET: dict[str, str] = {
    "luxury_traveler":   "luxury",
    "family_vacation":   "mid",
    "budget_traveler":   "budget",
    "honeymoon":         "luxury",
    "business_traveler": "mid",
    "wellness_spa":      "mid",
}

_PROFILE_AGE: dict[str, dict[str, float]] = {
    "luxury_traveler":   {"18-24": 0.05, "25-34": 0.15, "35-44": 0.30, "45-54": 0.30, "55+": 0.20},
    "family_vacation":   {"18-24": 0.05, "25-34": 0.25, "35-44": 0.40, "45-54": 0.25, "55+": 0.05},
    "budget_traveler":   {"18-24": 0.35, "25-34": 0.40, "35-44": 0.15, "45-54": 0.07, "55+": 0.03},
    "honeymoon":         {"18-24": 0.25, "25-34": 0.50, "35-44": 0.20, "45-54": 0.05, "55+": 0.00},
    "business_traveler": {"18-24": 0.03, "25-34": 0.25, "35-44": 0.35, "45-54": 0.30, "55+": 0.07},
    "wellness_spa":      {"18-24": 0.05, "25-34": 0.15, "35-44": 0.30, "45-54": 0.30, "55+": 0.20},
}

_DEVICE_WEIGHTS: dict[str, float] = {"mobile": 0.58, "desktop": 0.35, "tablet": 0.07}

_SOURCE_CITIES = [
    "Ankara", "İstanbul", "İzmir", "Bursa", "Adana",
    "Gaziantep", "Konya", "Kayseri", "Mersin",
    "Almanya", "Hollanda", "İngiltere", "Rusya", "Suudi Arabistan",
]

# ─── Event sabitleri ──────────────────────────────────────────────────────────

# Bu event tipleri otel kaydı gerektirir
_HOTEL_EVENTS = {"hotel_view", "favorite_added", "reservation_click", "whatsapp_click", "website_redirect"}

_PROFILE_FILTERS: dict[str, list[str]] = {
    "luxury_traveler":   ["stars_5", "spa", "beach_access", "suite_room"],
    "family_vacation":   ["kids_club", "family_room", "all_inclusive", "pool"],
    "budget_traveler":   ["price_low", "discount", "early_booking_deal"],
    "honeymoon":         ["romantic_package", "sea_view", "honeymoon_suite", "jacuzzi"],
    "business_traveler": ["wifi", "central_location", "late_checkout", "meeting_room"],
    "wellness_spa":      ["spa", "hammam", "yoga_program", "detox_package"],
}

_SOURCE_CHANNEL: dict[str, list[str]] = {
    "luxury_traveler":   ["web", "web", "campaign"],
    "family_vacation":   ["web", "mobile", "campaign"],
    "budget_traveler":   ["mobile", "campaign", "web"],
    "honeymoon":         ["web", "mobile", "campaign"],
    "business_traveler": ["web", "web", "mobile"],
    "wellness_spa":      ["mobile", "web", "campaign"],
}


# ─── Ana sınıf ───────────────────────────────────────────────────────────────

class SyntheticDataGenerator:
    """
    Gerçekçi sentetik CRM verisi üretir ve SQLite veritabanına yazar.

    Kullanım:
        gen = SyntheticDataGenerator()
        summary = gen.generate(reset=True)
    """

    def __init__(
        self,
        n_hotels: int = 30,
        n_users: int = 500,
        n_events: int = 5000,
        seed: int = 42,
    ) -> None:
        self.n_hotels = n_hotels
        self.n_users = n_users
        self.n_events = n_events
        self.seed = seed

        # Hedef event sayıları (sabit)
        self._fixed: dict[str, int] = {
            "hotel_view":        1000,
            "reservation_click": 200,
            "whatsapp_click":    300,
            "favorite_added":    400,
        }
        remaining = n_events - sum(self._fixed.values())  # 3100
        self._flex: dict[str, int] = {
            "filter_used":      round(remaining * 0.48),   # ~1488
            "website_redirect": round(remaining * 0.32),   # ~992
            "campaign_click":   round(remaining * 0.20),   # ~620
        }
        # Yuvarlama farkını düzelt
        flex_diff = remaining - sum(self._flex.values())
        self._flex["filter_used"] += flex_diff

        random.seed(seed)
        np.random.seed(seed)

        # 6 aylık zaman aralığı
        self.end_dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
        self.start_dt = self.end_dt - timedelta(days=180)

    # ── Otel üretimi ─────────────────────────────────────────────────────────

    def _unique_name(self, city: str, district: str, used: set[str]) -> str:
        for _ in range(20):
            adj  = random.choice(_ADJECTIVES)
            tmpl = random.choice(_NAME_TEMPLATES)
            name = tmpl.format(city=city, district=district, adj=adj)
            if name not in used:
                return name
        return f"{district} Hotel {random.randint(100, 999)}"

    def _build_amenities(self, city: str, stars: int) -> list[str]:
        ams = list(_BASE_AMENITIES[stars])
        if city in BEACH_CITIES and stars >= 4:
            ams += [a for a in _BEACH_EXTRA if a not in ams]
        if stars == 5:
            ams += [a for a in _SPA_EXTRA if a not in ams]
        if stars >= 4:
            ams += [a for a in _FAMILY_EXTRA[:2] if a not in ams]
        if city in CITY_CENTERS and stars >= 4:
            ams += [a for a in _BIZ_EXTRA if a not in ams]
        if city in NATURE_CITIES:
            ams += [a for a in _NATURE_EXTRA[:2] if a not in ams]
        return list(dict.fromkeys(ams))  # deduplicate, order korunur

    def _build_profile_tags(self, city: str, stars: int, amenities: list[str]) -> list[str]:
        tags: set[str] = set()
        if stars == 5:
            tags.update(["luxury_traveler", "honeymoon"])
        if stars >= 4 and city in BEACH_CITIES:
            tags.update(["family_vacation", "honeymoon", "luxury_traveler"])
        if stars >= 4 and city in CITY_CENTERS:
            tags.add("business_traveler")
        if stars <= 3:
            tags.add("budget_traveler")
        if any(a in amenities for a in ("spa", "hammam", "sauna", "yoga")):
            tags.add("wellness_spa")
        if "kids_club" in amenities:
            tags.add("family_vacation")
        if city in NATURE_CITIES:
            tags.update(["wellness_spa", "luxury_traveler"])
        return list(tags) or ["budget_traveler"]

    def _hotel_coords(self, city: str) -> tuple[float, float]:
        base_lat, base_lon = CITY_COORDS.get(city, (39.0, 35.0))
        return (
            round(base_lat + random.uniform(-0.15, 0.15), 6),
            round(base_lon + random.uniform(-0.15, 0.15), 6),
        )

    def _generate_hotels(self) -> list[Hotel]:
        used_names: set[str] = set()
        hotels: list[Hotel] = []

        cities = list(CITY_DISTRICTS.keys())
        # Her şehirden en az 2 otel garantili
        city_pool: list[str] = cities * 2
        while len(city_pool) < self.n_hotels:
            city_pool.append(random.choice(cities))
        random.shuffle(city_pool)
        city_pool = city_pool[: self.n_hotels]

        for city in city_pool:
            district = random.choice(CITY_DISTRICTS[city])
            stars    = random.choices([3, 4, 5], weights=[0.28, 0.42, 0.30])[0]
            name     = self._unique_name(city, district, used_names)
            used_names.add(name)

            amenities    = self._build_amenities(city, stars)
            profile_tags = self._build_profile_tags(city, stars, amenities)
            p_min, p_max = _PRICE_RANGE[stars]
            lat, lon     = self._hotel_coords(city)

            slug = name.lower().translate(str.maketrans(" &,.'", "-----"))
            hotels.append(Hotel(
                name=name,
                city=city,
                district=district,
                address=f"{district} Mah., {city}",
                rating=round(random.uniform(3.5, 5.0), 1),
                review_count=random.randint(50, 2500),
                stars=stars,
                latitude=lat,
                longitude=lon,
                price_level=_PRICE_LEVEL[stars],
                price_min=round(random.uniform(p_min, p_min * 1.4), 2),
                price_max=round(random.uniform(p_max * 0.7, p_max), 2),
                description=f"{stars} yıldızlı {city}/{district} konumlu otel.",
                amenities=json.dumps(amenities, ensure_ascii=False),
                profile_tags=json.dumps(profile_tags, ensure_ascii=False),
                website_url=f"https://www.{slug.replace('-', '')}.com",
                booking_url=f"https://www.booking.com/hotel/tr/{slug}.html",
                whatsapp_url=f"https://wa.me/90{random.randint(5000000000, 5999999999)}",
                phone=f"+90 {random.randint(200, 599)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
            ))

        logger.info("%d otel oluşturuldu.", len(hotels))
        return hotels

    # ── Kullanıcı üretimi ─────────────────────────────────────────────────────

    def _generate_users(self) -> list[CRMUser]:
        profiles = list(_PROFILE_DISTRIBUTION.keys())
        p_weights = list(_PROFILE_DISTRIBUTION.values())
        devices   = list(_DEVICE_WEIGHTS.keys())
        d_weights = list(_DEVICE_WEIGHTS.values())
        users: list[CRMUser] = []

        for _ in range(self.n_users):
            profile  = random.choices(profiles, weights=p_weights)[0]
            age_dist = _PROFILE_AGE[profile]
            age_range = random.choices(list(age_dist.keys()), weights=list(age_dist.values()))[0]
            device   = random.choices(devices, weights=d_weights)[0]

            users.append(CRMUser(
                session_id=str(uuid.uuid4()),
                profile_type=profile,
                preferred_budget=_PROFILE_BUDGET[profile],
                travel_type=profile,
                age_range=age_range,
                device_type=device,
                city=random.choice(_SOURCE_CITIES),
            ))

        logger.info("%d kullanıcı oluşturuldu.", len(users))
        return users

    # ── Event havuzu ──────────────────────────────────────────────────────────

    def _build_event_pool(self) -> list[str]:
        """Hedef sayılara göre karıştırılmış event tipi listesi."""
        pool: list[str] = []
        for etype, count in {**self._fixed, **self._flex}.items():
            pool.extend([etype] * count)
        random.shuffle(pool)
        return pool

    # ── Tarih üretimi ─────────────────────────────────────────────────────────

    def _random_dt(self) -> datetime:
        """
        6 aylık aralıkta rastgele tarih; son 3 aya %60 ağırlık.
        İş günleri ve mesai saatleri daha yoğun.
        """
        if random.random() < 0.60:
            ref = self.end_dt - timedelta(days=90)
        else:
            ref = self.start_dt
        secs = int((self.end_dt - ref).total_seconds())
        dt = ref + timedelta(seconds=random.randint(0, secs))

        # Sabah 08:00 – 23:00 arası daha yoğun
        if random.random() < 0.75:
            dt = dt.replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
        return dt

    # ── Event meta verisi ─────────────────────────────────────────────────────

    def _event_metadata(self, event_type: str, profile: str, hotel: Optional[Hotel]) -> Optional[str]:
        meta: dict = {}

        if event_type == "filter_used":
            opts = _PROFILE_FILTERS.get(profile, ["price_low"])
            meta["filters"]       = random.sample(opts, k=random.randint(1, min(2, len(opts))))
            meta["results_count"] = random.randint(4, 50)

        elif event_type == "hotel_view" and hotel:
            meta["duration_sec"]   = random.randint(12, 300)
            meta["photos_viewed"]  = random.randint(0, 30)
            meta["tab"]            = random.choice(["overview", "photos", "rooms", "reviews", "map"])

        elif event_type == "reservation_click" and hotel:
            check_in = datetime.now() + timedelta(days=random.randint(7, 120))
            meta["check_in"]   = check_in.strftime("%Y-%m-%d")
            meta["nights"]     = random.randint(2, 14)
            meta["guests"]     = random.randint(1, 5)
            meta["room_type"]  = random.choice(["standard", "deluxe", "suite", "family", "penthouse"])

        elif event_type == "whatsapp_click" and hotel:
            meta["inquiry_type"] = random.choice(
                ["price", "availability", "package", "special_request", "transfer"]
            )

        elif event_type == "website_redirect" and hotel:
            meta["section"]  = random.choice(["booking", "gallery", "offers", "contact", "about"])

        elif event_type == "campaign_click":
            meta["campaign"]      = random.choice(
                ["summer_deal", "early_booking", "last_minute", "flash_sale", "honeymoon_pkg", "wellness_retreat"]
            )
            meta["discount_pct"]  = random.choice([10, 15, 20, 25, 30])

        elif event_type == "favorite_added" and hotel:
            meta["list_name"] = random.choice(["wishlist", "comparing", "shortlist"])

        return json.dumps(meta, ensure_ascii=False) if meta else None

    # ── Event üretimi ─────────────────────────────────────────────────────────

    def _generate_events(
        self,
        users: list[CRMUser],
        hotels: list[Hotel],
    ) -> list[UserEvent]:
        event_pool = self._build_event_pool()
        total = len(event_pool)

        # Kullanıcı başına event sayısı: lognormal (power-user dağılımı)
        raw    = np.random.lognormal(mean=2.3, sigma=0.8, size=self.n_users)
        counts = np.round(raw / raw.sum() * total).astype(int)
        diff   = total - int(counts.sum())
        counts[0] += diff  # yuvarlama farkı

        # Profil → tercih edilen oteller
        profile_hotels: dict[str, list[Hotel]] = {}
        for profile in _PROFILE_DISTRIBUTION:
            ph = [h for h in hotels if profile in json.loads(h.profile_tags or "[]")]
            profile_hotels[profile] = ph or hotels

        events: list[UserEvent] = []
        pool_idx = 0

        for user, count in zip(users, counts):
            profile   = user.profile_type
            preferred = profile_hotels[profile]
            channels  = _SOURCE_CHANNEL.get(profile, ["web"])
            session_id = str(uuid.uuid4())
            session_dt = self._random_dt()

            for i in range(int(count)):
                if pool_idx >= total:
                    break
                event_type = event_pool[pool_idx]
                pool_idx  += 1

                hotel: Optional[Hotel] = None
                if event_type in _HOTEL_EVENTS:
                    hotel = random.choice(preferred)

                # Oturum içi sıralı zaman (max 45 dk yayılım)
                offset = timedelta(seconds=random.randint(30, 2700) * (i + 1))
                event_dt = session_dt + offset
                if event_dt > self.end_dt:
                    event_dt = self._random_dt()

                events.append(UserEvent(
                    user_id=user.id,
                    hotel_id=hotel.id if hotel else None,
                    event_type=event_type,
                    event_date=event_dt,
                    session_id=session_id,
                    source=random.choice(channels),
                    metadata_json=self._event_metadata(event_type, profile, hotel),
                ))

            # %35 ihtimalle sonraki oturumu farklı günde başlat
            if random.random() < 0.35:
                session_id = str(uuid.uuid4())
                session_dt = self._random_dt()

        logger.info("%d event oluşturuldu.", len(events))
        return events

    # ── Veritabanı işlemleri ─────────────────────────────────────────────────

    def create_tables(self) -> None:
        """CRM tablolarını oluşturur (varsa atlar)."""
        import src.crm.models  # noqa: F401 — Base'e kayıt için gerekli
        Base.metadata.create_all(bind=engine)
        logger.info("CRM tabloları hazır.")

    def reset(self) -> None:
        """Mevcut hotels, crm_users ve user_events kayıtlarını temizler."""
        with get_db() as db:
            db.query(UserEvent).delete()
            db.query(CRMUser).delete()
            db.query(Hotel).delete()
        logger.info("Mevcut CRM verileri temizlendi.")

    def export_csv(self) -> None:
        """Verileri data/ klasörüne CSV olarak aktarır."""
        import pandas as pd
        out = config.DATA_DIR
        out.mkdir(parents=True, exist_ok=True)
        with engine.connect() as conn:
            for table, fname in [
                ("hotels",      "hotels.csv"),
                ("crm_users",   "crm_users.csv"),
                ("user_events", "user_events.csv"),
            ]:
                df = pd.read_sql_table(table, con=conn)
                path = out / fname
                df.to_csv(path, index=False, encoding="utf-8-sig")
                logger.info("%s aktarıldı: %d satır → %s", fname, len(df), path)

    def generate(self, reset: bool = False) -> dict[str, int]:
        """
        Sentetik veriyi üretir ve veritabanına yazar.

        Args:
            reset: True ise mevcut CRM verisini önce siler.

        Returns:
            Üretilen kayıt sayılarını içeren sözlük.
        """
        self.create_tables()
        if reset:
            self.reset()

        logger.info("Veri üretimi başlıyor (seed=%d)...", self.seed)

        with get_db() as db:
            hotels = self._generate_hotels()
            db.add_all(hotels)
            db.flush()  # id'leri al

            users = self._generate_users()
            db.add_all(users)
            db.flush()  # id'leri al

            events = self._generate_events(users, hotels)
            db.add_all(events)
            # with bloğu bitince commit otomatik yapılır

        # İstatistik özeti
        from sqlalchemy import func as sqlfunc

        with get_db() as db:
            event_counts = dict(
                db.query(UserEvent.event_type, sqlfunc.count(UserEvent.id))
                .group_by(UserEvent.event_type)
                .all()
            )

        summary: dict[str, int] = {
            "hotels":       len(hotels),
            "crm_users":    len(users),
            "total_events": sum(event_counts.values()),
            **event_counts,
        }
        logger.info("Üretim tamamlandı: %s", summary)
        return summary
