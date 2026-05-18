# SuggesMe

**Küratörlük tabanlı otel keşif ve işletme CRM analitiği platformu.**

Seyahat edenlere küratörler tarafından seçilmiş oteller sunar; işletme sahiplerine ise
kullanıcı davranışı analizi, RFM segmentasyonu ve kampanya otomasyonu sağlar.

---

## İş Modeli

| Taraf | Değer |
|---|---|
| **Son Kullanıcı** | Küratörlenmiş, güvenilir otel önerileri; kişiselleştirilmiş keşif |
| **İşletme Sahibi** | Performans analitiği, rakip kıyaslaması, otomatik kampanya |
| **Küratör** | İçerik üretimi, güvenilirlik skoru, platforma katkı |
| **Platform** | Komisyon / abonelik; işletme onboarding geliri |

---

## Kullanıcı Akışı

```
Anasayfa → Otel Keşfet (filtrele) → Otel Detay (favorile / rezervasyon / WA)
         → Öneri Sistemi (profil bazlı öneriler)
```

## İşletme Sahibi Akışı

```
İşletme Onboarding (Google Maps'ten oteli bul & kaydet)
  → İşletme Paneli (KPI, trafik, rakip analizi)
  → RFM Analizi (segment oluştur)
  → Kampanya Otomasyonu (n8n webhook tetikle)
  → Instagram Zenginleştirme (public post'lardan özellik çıkar)
```

---

## Sistem Mimarisi

```
suggesme/
├── app/
│   ├── streamlit_app.py              # Ana uygulama — navigasyon anasayfa
│   └── pages/
│       ├── 1_Discovery.py            # Otel keşif ve filtreleme
│       ├── 2_Hotel_Detail.py         # Otel detay ve benzer oteller
│       ├── 3_Curator_Panel.py        # Küratör öneri yönetimi
│       ├── 4_Business_Panel.py       # İşletme KPI ve analitik paneli
│       ├── 5_CRM_RFM_Analytics.py   # RFM segmentasyon dashboardu
│       ├── 6_Campaign_Automation.py  # n8n webhook kampanya paneli
│       ├── 7_Business_Onboarding.py  # Google Maps ile işletme kaydı
│       ├── 8_Instagram_Enrichment.py # Public Instagram veri zenginleştirme
│       └── 9_Recommendations.py      # Cosine similarity + KMeans öneri
├── src/
│   ├── crm/
│   │   ├── models.py                 # Tüm ORM modelleri (10 tablo)
│   │   ├── rfm_analysis.py           # RFM hesaplama ve kaydetme
│   │   └── synthetic_data_generator.py
│   ├── business/
│   │   ├── business_dashboard_service.py  # KPI ve grafik hesapları
│   │   └── business_onboarding_service.py # Google Maps → hotels kaydı
│   ├── automation/
│   │   └── n8n_client.py             # Webhook gönderme ve kampanya log
│   ├── enrichment/
│   │   └── instagram_enrichment_service.py # Caption analizi, amenities güncelleme
│   ├── integrations/
│   │   ├── apify_maps_client.py      # Apify Google Maps scraper istemcisi
│   │   └── apify_instagram_client.py # Apify Instagram scraper istemcisi
│   ├── recommendation/
│   │   ├── recommender.py            # Cosine similarity öneri motoru
│   │   └── clustering.py             # KMeans otel segmentasyonu
│   ├── database/
│   │   ├── db.py                     # SQLAlchemy engine ve session
│   │   └── init_db.py                # Tablo oluşturma CLI
│   └── utils/
│       ├── config.py                 # .env yükleme ve Config sınıfı
│       ├── logger.py                 # Merkezi loglama
│       └── st_helpers.py             # Demo user, event tracking
├── scripts/
│   ├── generate_synthetic_data.py    # Sentetik veri CLI
│   ├── test_apify_maps.py            # Google Maps API testi
│   └── test_apify_instagram.py       # Instagram API testi
├── data/                             # SQLite veritabanı ve CSV exportlar
├── logs/                             # Uygulama logları
├── .env.example
├── requirements.txt
└── README.md
```

### Veritabanı Tabloları

| Tablo | Açıklama |
|---|---|
| `hotels` | 30 otel, 12 Türkiye şehri |
| `crm_users` | 500 demo kullanıcı, 6 profil tipi |
| `user_events` | 5 000 davranış eventi |
| `curators` | Küratörler |
| `curated_hotels` | Küratör–otel bağlantısı |
| `rfm_scores` | Kullanıcı RFM skorları (hesaplama sonrası) |
| `automation_events` | Gönderilen/simüle edilen kampanyalar |
| `business_accounts` | İşletme sahibi kaydı |
| `instagram_posts` | Çekilen public Instagram postları |
| `instagram_comments` | Post yorumları |

---

## Kullanılan Teknolojiler

| Katman | Teknoloji |
|---|---|
| **Arayüz** | Streamlit ≥ 1.35 |
| **Veritabanı** | SQLite + SQLAlchemy 2.0 ORM |
| **Veri İşleme** | pandas ≥ 2.0, numpy ≥ 1.26 |
| **Görselleştirme** | Plotly ≥ 5.20 |
| **ML** | scikit-learn ≥ 1.4 (KMeans) |
| **Yapılandırma** | python-dotenv |
| **Harici API** | Apify (Google Maps + Instagram) |
| **Otomasyon** | n8n webhook |

---

## Kurulum

### Gereksinimler

- Python 3.11+
- (İsteğe bağlı) Apify hesabı — Google Maps ve Instagram scraping için
- (İsteğe bağlı) n8n — kampanya webhook'u için

### 1. Depoyu klonla ve sanal ortam oluştur

```bash
git clone <repo-url>
cd suggesme

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Bağımlılıkları yükle

```bash
pip install -r requirements.txt
```

### 3. Ortam değişkenlerini ayarla

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

`.env` dosyasını düzenle — zorunlu alanlar:

```env
# Temel (değiştirmene gerek yok)
APP_ENV=development
DATABASE_URL=sqlite:///data/suggesme.db

# Apify (isteğe bağlı — boş bırakılırsa demo mod)
APIFY_API_TOKEN=your_token_here
APIFY_GOOGLE_MAPS_ACTOR_ID=compass/google-maps-scraper
APIFY_INSTAGRAM_ACTOR_ID=apify/instagram-scraper

# n8n (isteğe bağlı — boş bırakılırsa demo mod)
N8N_WEBHOOK_URL=https://your-n8n-instance/webhook/...
```

### 4. Klasörleri oluştur

```bash
mkdir data
mkdir logs
```

### 5. Veritabanını başlat

```bash
python src/database/init_db.py
```

---

## Sentetik Veri Oluşturma

```bash
# Standart (30 otel, 500 kullanıcı, 5 000 event)
python scripts/generate_synthetic_data.py --reset

# Özel parametreler
python scripts/generate_synthetic_data.py --reset --hotels 50 --users 1000 --events 10000

# Tekrarlanabilir veri (sabit seed)
python scripts/generate_synthetic_data.py --reset --seed 42

# CSV export (data/ klasörüne)
python scripts/generate_synthetic_data.py --reset --export-csv
```

**Üretilen veri:**

| Tür | Sayı |
|---|---|
| Oteller | 30 (İstanbul, Ankara, İzmir, Antalya, ...) |
| Kullanıcılar | 500 (6 profil: lüks, aile, ekonomik, balayı, iş, wellness) |
| hotel_view | 1 000 |
| reservation_click | 200 |
| whatsapp_click | 300 |
| favorite_added | 400 |
| website_redirect | ~992 |
| filter_used | ~1 488 |
| campaign_click | ~620 |

---

## Uygulamayı Çalıştırma

```bash
streamlit run app/streamlit_app.py
```

Tarayıcı otomatik açılır: **http://localhost:8501**

---

## Sayfa Rehberi

### 1. Otel Keşfet (`1_Discovery.py`)

Şehir, bütçe, seyahat tipi ve olanaklara göre filtrele. Otel kartlarından rezervasyon,
WhatsApp ve favoriye ekle aksiyonları izlenir.

### 2. Otel Detay (`2_Hotel_Detail.py`)

Harita, özellikler, benzer otel önerileri (+2 aynı şehir, +1 aynı fiyat, +1 ortak profil etiketi).

### 3. Küratör Paneli (`3_Curator_Panel.py`)

Küratör ekle / otel önerisi oluştur / mevcut önerileri yönet. 8 ön tanımlı kategori.

### 4. İşletme Paneli (`4_Business_Panel.py`)

Otel seç + tarih aralığı → 6 KPI kart + 5 Plotly grafik + 3 akıllı öneri.

Grafikler: günlük trend, event dağılımı, profil dağılımı, top oteller, rakip karşılaştırması.

### 5. RFM Analizi (`5_CRM_RFM_Analytics.py`)

"Analizi Hesapla ve Kaydet" → rfm_scores tablosuna yazar.

Segmentler: Champions, Loyal Customers, Potential Loyalists, New Customers, At Risk, Hibernating, Low Value.

Skorlama: R = son HIGH_VALUE event'ten gün (ters); F = toplam event; M = proxy ağırlıklı toplam.

### 6. Kampanya Otomasyonu (`6_Campaign_Automation.py`)

Segment + kanal + mesaj → n8n webhook tetikle (veya demo modda payload ekranında göster).
Tüm kampanyalar `automation_events` tablosuna kaydedilir.

### 7. İşletme Onboarding (`7_Business_Onboarding.py`)

4 adımlı sihirbaz: Ara → Seç → Bilgi Gir → Kaydet.
Apify Google Maps ile gerçek sonuçlar (token yoksa 5 demo otel).

### 8. Instagram Zenginleştirme (`8_Instagram_Enrichment.py`)

Public Instagram URL → post çek → caption'dan özellik çıkar → `hotels.amenities` güncelle.
25 Türkçe/İngilizce anahtar kelime ile kural tabanlı çıkarım.

### 9. Öneri Sistemi (`9_Recommendations.py`)

- **Tab 1:** Profil + bütçe → cosine similarity → kart öneri + bar grafik
- **Tab 2:** KMeans kümeleme (k ayarlanabilir) → pie, bar, tablo
- **Tab 3:** Referans otel seç → 4 benzer otel

---

## Apify Entegrasyonu

### Google Maps (İşletme Onboarding)

```bash
# Bağlantıyı test et
python scripts/test_apify_maps.py "Hilton Istanbul" --max 3

# Demo mod (token olmadan)
python scripts/test_apify_maps.py "Antalya Resort"
```

Actor: `compass/google-maps-scraper` (varsayılan)
Override: `.env` dosyasında `APIFY_GOOGLE_MAPS_ACTOR_ID` değişkeni

### Instagram Zenginleştirme

```bash
# Public profil test et
python scripts/test_apify_instagram.py https://www.instagram.com/username/ --max 5

# Demo mod (token olmadan)
python scripts/test_apify_instagram.py https://www.instagram.com/anyprofile/
```

Actor: `apify/instagram-scraper` (varsayılan)

---

## n8n Kampanya Otomasyonu

1. n8n'de yeni bir **Webhook** node oluştur
2. Webhook URL'ini `.env` dosyasına ekle: `N8N_WEBHOOK_URL=https://...`
3. "Kampanya Otomasyonu" sayfasından test kampanyası gönder

**Payload formatı:**
```json
{
  "campaign_name": "İndirim Kampanyası — Hotel X (Champions)",
  "hotel_name": "Hotel X",
  "segment": "Champions",
  "channel": "email",
  "campaign_type": "İndirim Kampanyası",
  "message": "VIP üyemiz olarak...",
  "target_user_count": 45,
  "created_at": "2026-05-15T10:30:00"
}
```

Token tanımlı değilse uygulama otomatik olarak **demo modda** çalışır — payload ekranda gösterilir, gerçek istek yapılmaz.

---

## RFM Analitiği — Teknik Detay

| Boyut | Hesaplama |
|---|---|
| **Recency (R)** | Son `reservation_click / whatsapp_click / website_redirect` tarihinden gün sayısı (ters skor) |
| **Frequency (F)** | Toplam event sayısı |
| **Monetary (M)** | `reservation_click×100 + whatsapp_click×70 + website_redirect×50 + favorite_added×20 + hotel_view×5 + campaign_click×30` |

Skorlama: `pd.qcut` ile 1–5 bant (duplicate-drop). Segment ataması kural tabanlı if-elif zinciri.

---

## Öneri Sistemi — Teknik Detay

**Özellik Vektörü (9 boyut):**
```
[price_level_norm, rating_norm, stars_norm,
 tag_luxury, tag_family, tag_budget,
 tag_honeymoon, tag_business, tag_wellness]
```

**Cosine Similarity:** Saf NumPy `dot(a,b) / (norm(a)×norm(b))` — ek bağımlılık yok.

**KMeans:** scikit-learn, n_init=10, küme adı centroid'in baskın tag + fiyat segmentinden türetilir.

---

## Güvenlik ve Etik Notlar

- **Private hesap verisi çekilmez** — sadece public Instagram profilleri/postları işlenir
- **DM scraping yapılmaz** — direkt mesaj ve özel içerikler kapsam dışıdır
- **Login gerektiren veri kullanılmaz** — tüm Apify çağrıları public endpoint'lere yapılır
- **Otomatik mesajlaşma için resmi API tercih edilmelidir** — n8n entegrasyonu simülasyon amaçlıdır; gerçek kampanya gönderimi için WhatsApp Business API veya e-posta servisi kullanılmalıdır
- **Kullanıcı verileri KVKK/GDPR uyumlu işlenmelidir** — demo'da gerçek kullanıcı verisi bulunmamaktadır; production'a geçişte veri minimizasyonu ve açık rıza mekanizmaları eklenmelidir
- **Demo veriler tamamen sentetiktir** — tüm kullanıcı ve otel verileri `SyntheticDataGenerator` ile üretilmiştir; gerçek kişi veya işletmeyle bağlantısı yoktur
- **API token'ları ekranda tam gösterilmez** — `masked_token()` fonksiyonu ile ilk 4 + son 4 karakter gösterilir

---

## Demo Senaryosu

### Hazırlık (1 dakika)

```bash
# 1. Sanal ortamı aktif et
venv\Scripts\activate

# 2. Sentetik veri oluştur (daha önce oluşturulmadıysa)
python scripts/generate_synthetic_data.py --reset

# 3. Uygulamayı başlat
streamlit run app/streamlit_app.py
```

### Demo Akışı (10–15 dakika)

#### A. Son Kullanıcı Deneyimi (3 dk)

1. **Anasayfa** → Tüm özelliklere genel bakış
2. **Otel Keşfet** → Şehir: İstanbul, Bütçe: Lüks → filtreleme göster
3. Bir otel kartından **"Detay"** tıkla → **Otel Detay** sayfası
4. Benzer oteller bölümünü göster; **WhatsApp** veya **Rezervasyon** butonuna bas (event kaydı)

#### B. Küratör Akışı (2 dk)

5. **Küratör Paneli** → "Otel Önerisi Ekle" sekmesi → hızlı bir öneri ekle
6. "Mevcut Öneriler" sekmesi → kayıtlı önerileri göster

#### C. İşletme Sahibi Analitiği (4 dk)

7. **İşletme Paneli** → Bir otel seç, Son 30 Gün → 6 KPI kart + grafikler göster
8. Rakip karşılaştırması bölümünü vurgula
9. **RFM Analizi** → "Analizi Hesapla ve Kaydet" → segment dağılımı ve kampanya önerileri
10. **Kampanya Otomasyonu** → Champions segmenti + email + mesaj → "Test Webhook Gönder"
    - Demo modda payload JSON ekranda gösterilir
    - Kampanya geçmişi tablosunda kayıt görünür

#### D. Zenginleştirme ve Öneri (3 dk)

11. **Instagram Zenginleştirme** → Bir otel seç → "Veri Çek" → demo postlar göster
    → "Verileri Kaydet" → "Kaydedilen Veriler" sekmesi → "Özellikleri Otele Uygula"
12. **Öneri Sistemi** → Profil: Lüks Seyahatçi, Bütçe: Lüks → öneriler listesi
    → "Küme Analizi" sekmesi → "Kümeleri Hesapla" → pie + tablo

#### E. Onboarding (isteğe bağlı, 2 dk)

13. **İşletme Onboarding** → "Yeni İşletme Kaydı" → otel adı + şehir ara (demo mod)
    → Demo listeden seç → Bilgiler gir → Kaydet → başarı ekranı

### Vurgulanacak Noktalar

| Özellik | Demo'da göster |
|---|---|
| Demo mod | API token olmadan tüm özellikler çalışır |
| Sentetik veri | 30 otel, 500 kullanıcı, 5 000 event — gerçekçi dağılım |
| Modüler mimari | Her sprint bağımsız bir özellik katmanı ekler |
| Açıklanabilir ML | 9 boyutlu vektör, cosine similarity, KMeans |
| Etik scraping | Sadece public veri, token maskeleme |

---

## Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| `ModuleNotFoundError` | `venv\Scripts\activate` sonra `pip install -r requirements.txt` |
| Boş otel listesi | `python scripts/generate_synthetic_data.py --reset` çalıştır |
| RFM hesaplanamadı | Önce sentetik veri üret, ardından RFM Analizi sayfasında butona bas |
| Apify 404 hatası | `APIFY_GOOGLE_MAPS_ACTOR_ID` değerini kontrol et — actor erişilebilir olmalı |
| n8n webhook hatası | URL'in n8n instance'ında aktif Webhook node'una işaret ettiğini doğrula |
| scikit-learn bulunamadı | `pip install scikit-learn>=1.4.0` |
