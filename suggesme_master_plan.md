# SuggesMe — Claude AI ile Sıfırdan Vibe Coding Proje Planı

> Bu doküman VS Code + Claude AI / Claude Code ile sıfırdan geliştirilecek **SuggesMe** projesi için hazırlanmıştır. Amaç, önce sağlam bir MVP çıkarmak; sonra Apify, n8n, CRM/RFM, recommendation ve işletme paneli özelliklerini kademeli olarak eklemektir.

---

## 1. Proje Tanımı

**SuggesMe**, küratörlük tabanlı otel keşif ve işletme CRM analitiği platformudur.

Platform iki ana kullanıcı tipine hizmet eder:

### 1.1 Son Kullanıcı
- Küratörlerin önerdiği otelleri keşfeder.
- Şehir, ilçe, bütçe, seyahat tipi, konsept ve özelliklere göre filtreleme yapar.
- Otel detay sayfasını inceler.
- Rezervasyon, WhatsApp veya websitesine yönlendirilir.
- Favori oteller ekleyebilir.

### 1.2 İşletme Sahibi
- Kendi otel profilini oluşturur veya Google Maps üzerinden işletmesini bulup sisteme ekler.
- Otel performansını takip eder.
- Görüntülenme, favori, rezervasyon tıklaması, WhatsApp tıklaması gibi metrikleri görür.
- RFM segmentlerine göre müşteri davranışlarını analiz eder.
- n8n webhook ile kampanya otomasyonu başlatır.

---

## 2. Ana Fikir

Instagram ve TikTok gibi platformlarda işletmeler görünürlük için sürekli reklam bütçesi harcar. Ancak kullanıcı beğendiği veya ilgilendiği işletmelere daha sonra düzenli ve filtrelenebilir şekilde ulaşamaz.

SuggesMe bu problemi şöyle çözer:

1. Küratörler otelleri seçer.
2. Platform bu otelleri filtrelenebilir ve kalıcı bir keşif havuzuna dönüştürür.
3. Kullanıcılar ihtiyaç duyduklarında otelleri yeniden keşfeder.
4. İşletmeler reklam yerine kalıcı görünürlük ve CRM verisi elde eder.
5. İşletme sahipleri kullanıcı ilgisini CRM, RFM ve kampanya otomasyonuna dönüştürür.

---

## 3. MVP Stratejisi

İlk sürümde gerçek Instagram DM listener, ödeme sistemi, gerçek rezervasyon altyapısı ve gelişmiş AI modelleri yapılmayacak.

Önce aşağıdaki MVP tamamlanacak:

1. Streamlit tabanlı web arayüzü
2. SQLite veritabanı
3. Otel keşif ekranı
4. Otel detay ekranı
5. Küratör paneli
6. İşletme paneli
7. Sentetik kullanıcı davranış verisi
8. RFM analizi
9. n8n webhook simülasyonu
10. Apify Google Maps ile işletme onboarding
11. Apify Instagram ile public veri enrichment

---

## 4. Teknoloji Stack

### Backend / Data
- Python
- SQLAlchemy
- SQLite MVP için
- PostgreSQL ileri aşamada
- pandas
- numpy

### Frontend / Dashboard
- Streamlit
- Plotly
- Pydeck veya Folium
- streamlit-folium

### Scraping / Data Collection
- Apify Python Client
- Google Maps Scraper Actor
- Instagram Public Data Scraper Actor

### Automation
- n8n webhook

### Machine Learning / Analytics
- RFM analysis
- Rule-based recommendation
- Rule-based topic classification
- Clustering ileri aşamada
- LLM enrichment ileri aşamada

---

## 5. Proje Klasör Yapısı

```text
suggesme/
│
├── app/
│   ├── streamlit_app.py
│   └── pages/
│       ├── 1_Discovery.py
│       ├── 2_Hotel_Detail.py
│       ├── 3_Curator_Panel.py
│       ├── 4_Business_Onboarding.py
│       ├── 5_Business_Panel.py
│       ├── 6_CRM_RFM_Analytics.py
│       └── 7_Campaign_Automation.py
│
├── src/
│   ├── database/
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   └── init_db.py
│   │
│   ├── data_collection/
│   │   ├── maps_apify_client.py
│   │   ├── instagram_apify_client.py
│   │   └── onboarding_service.py
│   │
│   ├── curation/
│   │   ├── curator_service.py
│   │   └── hotel_enrichment_service.py
│   │
│   ├── recommendation/
│   │   ├── recommender.py
│   │   └── clustering.py
│   │
│   ├── crm/
│   │   ├── synthetic_data_generator.py
│   │   ├── rfm_analysis.py
│   │   └── segmentation_service.py
│   │
│   ├── business/
│   │   └── business_dashboard_service.py
│   │
│   ├── automation/
│   │   └── n8n_client.py
│   │
│   └── utils/
│       ├── config.py
│       ├── logger.py
│       └── text_cleaner.py
│
├── data/
│   └── suggesme.db
│
├── scripts/
│   ├── seed_demo_data.py
│   ├── test_apify_connection.py
│   ├── test_maps_scraper.py
│   └── test_n8n_webhook.py
│
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── DATABASE_SCHEMA.md
│   ├── CLAUDE_PROMPTS.md
│   └── ROADMAP.md
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 6. Database Tabloları

### hotels
- id
- name
- city
- district
- address
- rating
- review_count
- latitude
- longitude
- instagram_url
- website_url
- booking_url
- whatsapp_url
- price_level
- description
- created_at
- updated_at

### hotel_features
- id
- hotel_id
- feature_name
- feature_value
- category

### curators
- id
- name
- instagram_username
- bio
- niche
- trust_score
- created_at

### curated_hotels
- id
- curator_id
- hotel_id
- source_post_url
- curator_note
- tags
- score
- created_at

### users
- id
- name
- email
- city
- preferred_budget
- travel_type
- created_at

### user_events
- id
- user_id
- hotel_id
- event_type
- event_date
- session_id
- source
- metadata_json

### business_accounts
- id
- hotel_id
- owner_name
- email
- subscription_plan
- created_at

### rfm_scores
- id
- user_id
- recency
- frequency
- monetary
- rfm_segment
- calculated_at

### campaigns
- id
- hotel_id
- segment_name
- campaign_name
- channel
- message
- status
- created_at

### automation_events
- id
- campaign_id
- event_type
- payload_json
- status
- created_at

### scraper_runs
- id
- source_type
- query
- status
- started_at
- finished_at
- total_items
- error_message

---

## 7. Event Tracking Mantığı

Aşağıdaki davranışlar `user_events` tablosuna kaydedilecek:

```text
hotel_view
filter_used
favorite_added
reservation_click
whatsapp_click
website_redirect
campaign_click
```

RFM analizi bu eventlerden üretilecek.

---

## 8. RFM Mantığı

### Recency
Kullanıcının son yüksek değerli etkileşim tarihi.

Yüksek değerli eventler:
- reservation_click
- whatsapp_click
- website_redirect

### Frequency
Kullanıcının toplam etkileşim sayısı.

### Monetary
Gerçek ödeme olmadığı için proxy skor kullanılacak:

```text
reservation_click = 100
whatsapp_click = 70
website_redirect = 50
favorite_added = 20
hotel_view = 5
filter_used = 2
campaign_click = 30
```

### Segmentler
- Champions
- Loyal Customers
- Potential Loyalists
- New Customers
- At Risk
- Hibernating
- Low Value

---

## 9. Recommendation Mantığı

İlk MVP’de basit kural tabanlı öneri yapılacak.

Kriterler:
- şehir
- ilçe
- bütçe seviyesi
- seyahat tipi
- otel konsepti
- rating
- favori ve tıklama davranışı
- küratör skoru

İleri aşamada:
- clustering
- collaborative filtering
- content-based recommendation
- LLM tabanlı otel açıklama ve eşleştirme

---

## 10. Apify Kullanım Mantığı

### 10.1 Google Maps Apify
Kullanım amacı:
- işletme onboarding
- otel keşfi
- otel temel bilgilerinin sisteme alınması

Akış:
1. İşletme sahibi otel adı ve şehir girer.
2. Sistem Apify Google Maps Scraper ile sonuçları çeker.
3. Kullanıcı kendi işletmesini seçer.
4. Otel kaydı hotels tablosuna eklenir.
5. business_accounts tablosunda işletme hesabı oluşturulur.

### 10.2 Instagram Apify
Kullanım amacı:
- public Instagram profil/post/comment enrichment
- otelin sosyal medya görünürlüğünü analiz etmek

Not:
- Private veri çekilmeyecek.
- DM scraping yapılmayacak.
- Otomatik DM için ileride resmi Meta API düşünülmeli.

---

## 11. n8n Kullanım Mantığı

İlk MVP’de gerçek mesaj gönderimi yapılmayacak.

n8n sadece webhook ile tetiklenecek.

Payload örneği:

```json
{
  "campaign_name": "VIP Erken Rezervasyon",
  "hotel_name": "Demo Hotel",
  "segment": "Champions",
  "channel": "email",
  "message": "Size özel erken rezervasyon fırsatı.",
  "target_user_count": 120,
  "created_at": "2026-01-01T12:00:00"
}
```

---

# 12. Claude AI ile Adım Adım Geliştirme Promptları

Aşağıdaki promptları Claude AI’ye sırayla ver.

---

## Prompt 1 — Proje Başlatma

```text
Sen profesyonel bir full stack Python yazılım mimarısın.

VS Code içinde sıfırdan SuggesMe adında bir proje geliştiriyoruz.

Proje amacı:
SuggesMe, küratörlük tabanlı otel keşif ve işletme CRM analitiği platformudur.

İki kullanıcı tipi olacak:
1. Son kullanıcı: otel keşfeder, filtreler, detay sayfasına girer, rezervasyon/WhatsApp/websitesine yönlendirilir.
2. İşletme sahibi: otelini sisteme ekler, performans metriklerini görür, RFM segmentlerine göre kampanya otomasyonu başlatır.

Öncelik Streamlit tabanlı MVP.

Şimdilik yapılmayacaklar:
- gerçek ödeme sistemi
- gerçek rezervasyon sistemi
- gerçek Instagram DM listener
- private Instagram veri scraping
- gerçek kullanıcı authentication

Önce sadece proje klasör yapısını oluştur.
requirements.txt, .env.example, .gitignore ve README.md dosyalarını oluştur.
Henüz iş mantığı kodlama.
```

---

## Prompt 2 — requirements ve environment

```text
requirements.txt dosyasını oluştur.

Kullanılacak paketler:
streamlit
pandas
numpy
sqlalchemy
python-dotenv
apify-client
plotly
scikit-learn
requests
folium
streamlit-folium
pydeck
faker

.env.example dosyasını oluştur:
APIFY_API_TOKEN=
APIFY_GOOGLE_MAPS_ACTOR_ID=
APIFY_INSTAGRAM_ACTOR_ID=
DATABASE_URL=sqlite:///data/suggesme.db
N8N_WEBHOOK_URL=
DEMO_MODE=true

.gitignore dosyasına ekle:
.env
venv/
__pycache__/
*.pyc
data/*.db
.streamlit/secrets.toml
```

---

## Prompt 3 — Config sistemi

```text
src/utils/config.py dosyasını oluştur.

İstekler:
- pathlib ile proje root dizinini bul
- .env dosyasını root dizinden explicit path ile yükle
- environment değişkenlerini strip() ile oku
- token değerlerini asla tam loglama
- DEMO_MODE true/false olarak okunabilsin
- APIFY_API_TOKEN varsa demo mode kapatılabilsin

Ayrıca scripts/test_config.py oluştur.
Bu script .env değişkenlerinin okunup okunmadığını güvenli şekilde test etsin.
Token varsa sadece ilk 10 karakter ve uzunluk yazdırılsın.
```

---

## Prompt 4 — Database modelleri

```text
SQLAlchemy ile database katmanını oluştur.

Dosyalar:
src/database/db.py
src/database/models.py
src/database/init_db.py

Tablolar:
- hotels
- hotel_features
- curators
- curated_hotels
- users
- user_events
- business_accounts
- rfm_scores
- campaigns
- automation_events
- scraper_runs

Her tablo için created_at alanı olsun.
Gerekli foreign key ilişkilerini kur.

scripts/init_db.py dosyasını da oluştur.
Komut:
python scripts/init_db.py
çalıştırıldığında database oluşturulsun.
```

---

## Prompt 5 — Repository katmanı

```text
src/database/repositories.py dosyasını oluştur.

Repository fonksiyonları:
- create_hotel
- list_hotels
- get_hotel_by_id
- update_hotel
- create_user
- create_user_event
- list_user_events
- create_business_account
- list_business_accounts
- save_rfm_score
- list_rfm_scores
- create_campaign
- create_automation_event

Kodlar modüler, okunabilir ve hata yönetimli olsun.
```

---

## Prompt 6 — Sentetik veri üretimi

```text
src/crm/synthetic_data_generator.py dosyasını oluştur.

Amaç:
Platform bir süredir çalışıyormuş gibi demo veri üretmek.

Üretilecekler:
- 30 otel
- 5 küratör
- 500 kullanıcı
- 5000 user_event
- 10 business_account

Kullanıcı profilleri:
- luxury_traveler
- family_vacation
- budget_traveler
- honeymoon
- business_traveler
- wellness_spa

Event tipleri:
- hotel_view
- filter_used
- favorite_added
- reservation_click
- whatsapp_click
- website_redirect
- campaign_click

scripts/seed_demo_data.py oluştur.
Komut:
python scripts/seed_demo_data.py
çalışınca demo veriler database’e eklensin.
```

---

## Prompt 7 — Ana Streamlit uygulaması

```text
app/streamlit_app.py dosyasını oluştur.

Ana sayfada:
- SuggesMe başlığı
- ürün açıklaması
- iki ana kart:
  1. Otel keşfet
  2. İşletme paneli
- MVP kapsamı
- demo veri durumu
- hızlı yönlendirme linkleri

Streamlit multipage yapısına uygun olsun.
```

---

## Prompt 8 — Discovery sayfası

```text
app/pages/1_Discovery.py sayfasını oluştur.

Amaç:
Son kullanıcı otel keşfi yapabilsin.

Filtreler:
- şehir
- ilçe
- bütçe seviyesi
- seyahat tipi
- minimum rating
- özellik arama

Otel kartlarında:
- otel adı
- şehir/ilçe
- rating
- review_count
- price_level
- kısa açıklama
- rezervasyona git butonu
- WhatsApp butonu
- websitesi butonu
- favoriye ekle butonu

Butonlara basılınca user_events tablosuna event kaydedilsin.
Şimdilik demo user_id kullanılabilir.
```

---

## Prompt 9 — Otel detay sayfası

```text
app/pages/2_Hotel_Detail.py oluştur.

İçerik:
- otel seçimi
- otel bilgileri
- harita konumu
- özellikler
- küratör notları
- benzer oteller
- rezervasyon / WhatsApp / website butonları

Her buton event tracking yapsın.
Benzer oteller için src/recommendation/recommender.py içinde basit kural tabanlı öneri fonksiyonu yaz.
```

---

## Prompt 10 — Küratör paneli

```text
app/pages/3_Curator_Panel.py oluştur.

Küratör işlemleri:
- küratör seçimi
- otel seçimi
- Instagram post URL ekleme
- küratör notu yazma
- etiket ekleme
- skor verme
- curated_hotels tablosuna kaydetme

Etiket örnekleri:
romantik kaçamak, aile tatili, lüks deneyim, butik otel, gastronomi, doğa tatili, spa wellness
```

---

## Prompt 11 — Business onboarding + Apify Maps

```text
app/pages/4_Business_Onboarding.py oluştur.

Amaç:
İşletme sahibi otelini Google Maps üzerinden bulup sisteme ekleyebilsin.

src/data_collection/maps_apify_client.py oluştur.

Fonksiyonlar:
- test_apify_connection()
- search_hotels_on_maps(query, max_results)
- normalize_maps_results(raw_items)

Önemli:
- APIFY_API_TOKEN authentication için kullanılacak
- APIFY_GOOGLE_MAPS_ACTOR_ID actor id için kullanılacak
- Eğer APIFY_GOOGLE_MAPS_ACTOR_ID içinde apify_api_ geçiyorsa kullanıcıya açık hata ver
- Eğer token yoksa demo mode ile örnek otel sonuçları dön

Business onboarding sayfasında:
- otel adı input
- şehir input
- ara butonu
- sonuçları tablo göster
- seçilen oteli hotels tablosuna kaydet
- işletme sahibi bilgileri ile business_account oluştur
```

---

## Prompt 12 — İşletme paneli

```text
app/pages/5_Business_Panel.py oluştur.

İşletme sahibi otel seçsin ve şu metrikleri görsün:

KPI kartları:
- toplam görüntülenme
- rezervasyon tıklaması
- WhatsApp tıklaması
- website tıklaması
- favoriye eklenme
- dönüşüm oranı

Grafikler:
- günlük event trendi
- event dağılımı
- kullanıcı profili dağılımı
- en çok ilgi gören oteller

src/business/business_dashboard_service.py içinde hesaplama fonksiyonları yaz.
```

---

## Prompt 13 — RFM analizi

```text
src/crm/rfm_analysis.py oluştur.

RFM hesaplama:
Recency: son yüksek değerli event tarihi
Frequency: toplam event sayısı
Monetary: proxy değer

Proxy skor:
reservation_click = 100
whatsapp_click = 70
website_redirect = 50
favorite_added = 20
hotel_view = 5
filter_used = 2
campaign_click = 30

Segmentler:
- Champions
- Loyal Customers
- Potential Loyalists
- New Customers
- At Risk
- Hibernating
- Low Value

Fonksiyonlar:
- calculate_rfm_scores
- assign_rfm_segment
- save_rfm_scores
- get_segment_summary

app/pages/6_CRM_RFM_Analytics.py oluştur.
Dashboard’da segment dağılımı, RFM tablo ve kampanya önerileri göster.
```

---

## Prompt 14 — n8n kampanya otomasyonu

```text
src/automation/n8n_client.py oluştur.

Fonksiyonlar:
- send_campaign_webhook(payload)
- build_campaign_payload(hotel, segment, campaign_name, channel, message, target_user_count)

app/pages/7_Campaign_Automation.py oluştur.

Arayüz:
- otel seçimi
- segment seçimi
- kanal seçimi: email, whatsapp, instagram, sms
- kampanya adı
- mesaj şablonu
- test webhook gönder butonu

Gerçek mesaj gönderimi yapılmayacak.
Sadece n8n webhook tetiklenecek ve automation_events tablosuna kayıt atılacak.
```

---

## Prompt 15 — Instagram enrichment

```text
src/data_collection/instagram_apify_client.py oluştur.

Amaç:
Otelin public Instagram verisini enrichment amacıyla çekmek.

Fonksiyonlar:
- test_instagram_actor_config()
- scrape_instagram_profile(instagram_url, max_posts)
- normalize_instagram_results(raw_items)

Kurallar:
- private veri çekilmeyecek
- DM çekilmeyecek
- login gerektiren veri çekilmeyecek
- sadece public profil/post/comment verisi kullanılacak

Otel detay sayfasına Instagram enrichment alanı ekle:
- toplam post
- toplam beğeni
- en çok etkileşim alan post
- en sık geçen temalar
```

---

## Prompt 16 — README tamamlama

```text
README.md dosyasını baştan düzenle.

Bölümler:
1. SuggesMe nedir?
2. Problem
3. Çözüm
4. Kullanıcı tipleri
5. MVP özellikleri
6. Teknoloji stack
7. Kurulum
8. .env ayarları
9. Demo veri oluşturma
10. Streamlit çalıştırma
11. Apify Maps entegrasyonu
12. Apify Instagram entegrasyonu
13. RFM analitiği
14. n8n kampanya otomasyonu
15. Güvenlik ve etik notlar
16. Roadmap

Kurulum komutları Windows için yazılsın.
```

---

# 13. Terminal Komutları

Yeni proje klasörü içinde:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_demo_data.py
streamlit run app/streamlit_app.py
```

---

# 14. .env Örneği

```env
APIFY_API_TOKEN=
APIFY_GOOGLE_MAPS_ACTOR_ID=
APIFY_INSTAGRAM_ACTOR_ID=
DATABASE_URL=sqlite:///data/suggesme.db
N8N_WEBHOOK_URL=
DEMO_MODE=true
```

Gerçek Apify kullanırken:

```env
DEMO_MODE=false
APIFY_API_TOKEN=apify_api_xxxxxxxxx
APIFY_GOOGLE_MAPS_ACTOR_ID=BURAYA_GOOGLE_MAPS_ACTOR_ID
APIFY_INSTAGRAM_ACTOR_ID=BURAYA_INSTAGRAM_ACTOR_ID
```

---

# 15. Güvenlik ve Etik Notlar

- `.env` dosyası asla GitHub’a gönderilmemeli.
- API token ekran görüntüsü veya chat ortamında paylaşılmamalı.
- Instagram private veri çekilmemeli.
- DM scraping MVP kapsamına alınmamalı.
- Kullanıcı verileri KVKK/GDPR uyumlu işlenmeli.
- Otomatik mesaj gönderimi için resmi API’ler tercih edilmeli.
- n8n ilk aşamada sadece test webhook simülasyonu olarak kullanılmalı.

---

# 16. Geliştirme Sırası

En doğru sıra:

```text
1. Proje iskeleti
2. requirements + .env
3. config sistemi
4. database modelleri
5. demo veri üretimi
6. Streamlit ana ekran
7. Discovery sayfası
8. Otel detay sayfası
9. Küratör paneli
10. Business onboarding
11. Business panel
12. RFM analizi
13. n8n kampanya otomasyonu
14. Apify Maps gerçek entegrasyon
15. Apify Instagram enrichment
16. Recommendation ve clustering
```

---

# 17. Claude AI Kullanım Kuralı

Claude’a her seferinde yalnızca bir sprint ver.

Yanlış kullanım:

```text
Tüm projeyi baştan sona yap.
```

Doğru kullanım:

```text
Sadece database modellerini oluştur. Kodları çalıştırılabilir yaz. Sonra dur ve benden test sonucu bekle.
```

Her adımdan sonra terminalde test yap:

```bash
python scripts/init_db.py
python scripts/seed_demo_data.py
streamlit run app/streamlit_app.py
```

---

# 18. İlk Claude Komutu

Yeni VS Code projesini açtıktan sonra Claude’a ilk olarak bunu ver:

```text
Bu projeye sıfırdan başlıyoruz.

Proje adı: SuggesMe

Kök dizinde bulunan suggesme_claude_ai_vibe_coding_master_plan.md dosyasını oku.
Bu dokümanı ana referans kabul et.

Şimdilik sadece Prompt 1’i uygula:
- proje klasör yapısını oluştur
- requirements.txt oluştur
- .env.example oluştur
- .gitignore oluştur
- README.md başlangıç dosyasını oluştur

Henüz database, Streamlit sayfaları veya Apify kodu yazma.
Her dosyanın ne işe yaradığını kısa açıklamalarla belirt.
```

