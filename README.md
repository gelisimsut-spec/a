# MCS Beton Operasyon Merkezi

`MCSSoft_New.sqlite` veritabanına bağlanan, beton santrali operasyonları ve muhasebe süreçlerini tek arayüzde yöneten profesyonel bir Streamlit uygulaması.

## Modüller

- **Dashboard**
  - Toplam cari / sipariş / açık sipariş / tamamlanan sipariş KPI kartları
  - Son sipariş akışı ve reçete bazlı üretim grafiği

- **Cari Yönetimi**
  - `Musteri` tablosundan cari listeleme
  - Yeni cari açma (firma adı, vergi no, adres, telefon)
  - Cari düzenleme
  - Aktif/pasif filtreleme ve bakiye görünümü

- **Sipariş Yönetimi**
  - `Siparis` üzerinden cari bazlı sipariş açma
  - `Recete` ve `Hizmet` seçimi ile sipariş oluşturma
  - Durum yönetimi: `beklemede`, `üretimde`, `tamamlandı`
  - Siparişten üretime otomatik aktarım (`UretimPlan`)

- **Muhasebe**
  - `Hareketler` üzerinden cari bakiye görüntüleme
  - Ödeme/tahsilat girişi
  - Cari hesap hareketleri listesi
  - Cari bazlı borç-alacak raporu
  - Excel/PDF dışa aktarım

- **Santral Entegrasyonu**
  - Reçete bazlı üretim planı
  - Planlanan/üretilen miktar takibi
  - Üretim raporları ve durum kırılımı

## Teknoloji

- **UI**: Streamlit
- **ORM**: SQLAlchemy
- **DB**: SQLite (`MCSSoft_New.sqlite`)
- **Raporlama**: Pandas + OpenPyXL + ReportLab

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Not

Uygulama ilk açılışta aşağıdaki tabloları otomatik oluşturur:

- `Hareketler`
- `SiparisDurum`
- `UretimPlan`

Bu tablolar mevcut yapı ile uyumlu şekilde ek modüller için kullanılır.


## Telif Hakkı

© 2026 Morina Tech. Tüm hakları saklıdır.
