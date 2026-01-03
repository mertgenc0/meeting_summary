# 📊 Microsoft Teams Meeting Transcript Automation

Bu proje, **Microsoft Teams toplantılarının transcript (konuşma dökümü)** verilerini **Microsoft Graph API** üzerinden otomatik olarak çekip, **n8n** ile uçtan uca bir otomasyon hattı kurarak özetlenmesini, PDF haline getirilmesini ve e-posta ile gönderilmesini amaçlayan **deneme / kendini geliştirme odaklı** bir projedir.

Proje; Python, PostgreSQL, n8n ve LLM (Gemini) entegrasyonlarını bir arada kullanarak gerçek hayatta kullanılabilecek profesyonel bir otomasyon mimarisi sunar.

---

## 🚀 Proje Özeti

Akış şu şekildedir:

1. **Microsoft Graph API** ile son 24 saat içindeki Teams toplantıları alınır.
2. Toplantıya ait **transcript (VTT formatında)** çekilir.
3. Transcript temizlenir ve işlenir.
4. Çıktılar **PostgreSQL** veritabanına kaydedilir.
5. **n8n** üzerinden:

   * Gemini ile toplantı özeti oluşturulur
   * Özet HTML formatında üretilir
   * HTML → PDF dönüşümü yapılır (**PDF.co API**) 
   * PDF özeti veritabanı ile merge edilir
   * PDF, e-posta eki olarak otomatik gönderilir

---

## 🧠 Kullanılan Teknolojiler

* **Python**
* **Microsoft Graph API** (Teams & Calendar)
* **Microsft Permission (Powershell)
* **PostgreSQL**
* **n8n** (Workflow Automation)
* **Gemini (LLM)** – Toplantı özeti
* **PDF.co API** – HTML to PDF
* **Docker / Local Server** (opsiyonel)

---

## 🏗️ Sistem Mimarisi

```text
Scheduler Trigger
      ↓
Execute Command (Python Script)
      ↓
PostgreSQL (Upsert)
      ↓
      ├──▶ Gemini (Meeting Summary)
      │        ↓
      │    HTML Output
      │        ↓
      │    PDF.co (HTML → PDF)
      │        ↓
      └────────▶ Merge
                   ↓
               Mail Send (PDF Ekli)
```
![n8nworkflow.png](images%2Fn8nworkflow.png)

## 📧 Otomatik Gönderilen Mail Çıktısı

![mailoutput.png](images%2Fmailoutput.png)
---
## 🐍 Python Script – Ne Yapıyor?

Python scripti aşağıdaki görevleri yerine getirir:

* OAuth2 **Client Credentials Flow** ile access token alır
* Son **24 saat** içindeki toplantıları çeker
* `joinUrl` üzerinden **duplicate kontrolü** yapar
* Transcript içeriğini **VTT → temiz metin** formatına dönüştürür
* Yeni toplantıları çıktı olarak verir. (n8n'de işlemlerin yapılmasına hazır hale getirir)

### 🔒 Duplicate Kontrolü

Aynı toplantının birden fazla kez işlenmesini önlemek için:

```sql
SELECT 1 FROM meetings WHERE join_url = %s
```

kontrolü yapılır.
---

## 🗂️ Ortam Değişkenleri (.env)

```env
# Microsoft Graph
TENANT_ID=
CLIENT_ID=
CLIENT_SECRET=
USER_ID=

# PostgreSQL
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

---

## 🔁 n8n Workflow Açıklaması

### 1️⃣ Scheduler Trigger

* Workflow her gün otomatik çalışır

### 2️⃣ Execute Command

* Python script tetiklenir
* JSON çıktısı alınır

### 3️⃣ PostgreSQL (Upsert)

* Yeni toplantılar veritabanına eklenir

### 4️⃣ Gemini (gemini-2.5-flash)

* Transcript üzerinden toplantı özeti çıkarılır
* HTML formatında çıktı üretilir

### 5️⃣ PDF.co API

* HTML içeriği PDF’e dönüştürülür

### 6️⃣ Merge & Mail Send

* PDF ve database birleştirilir
* PDF, e-posta eki olarak gönderilir

---

## 📌 Projenin Amacı

Bu proje:

* n8n + Python hibrit otomasyon mantığını öğrenmek
* Microsoft Graph API ile gerçek veri kullanmak
* DataBase bağlantıalrı hakkında bilgi sahibi olmak
* LLM tabanlı meeting summary sistemleri geliştirmek
* Low-code & code-first yaklaşımları karşılaştırmak

amaçlarıyla geliştirilmiştir.

---

## ⚠️ Notlar

* Proje **deneme / öğrenme amaçlıdır**
* Production ortamına alınmadan önce:

  * Rate limit
  * Error handling
  * Logging
  * Security hardening

eklenmelidir.

> **Not:** Bu proje; model seçimi, özetleme stratejileri, event-driven mimari,Python ile PDF çıkarma, kullanıcı arayüzü entegrasyonu gibi birçok farklı açıdan geliştirilmeye açıktır.  
> Ancak mevcut haliyle hedeflenen öğrenme ve deneyim kazanımı sağlandığı için bu aşamada yeterli görülmüş ve  yeni projelere odaklanılmaya baaşlayacağım.


---

## 📬 İletişim

Her türlü geri bildirim ve geliştirme önerisine açığım 🚀

> *Bu proje, otomasyon ve yapay zekâ entegrasyonları üzerine kendimi geliştirmek amacıyla oluşturulmuştur.*

