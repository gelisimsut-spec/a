# Beton Santrali Yönetim Arayüzü

Bu proje, `MCSSoft_New.sqlite` veritabanını kullanarak beton santrali + muhasebe süreçlerini tek bir arayüzde yönetmek için hazırlanmış bir Streamlit uygulamasıdır.

## Özellikler

- **Cari Yönetimi**
  - `Musteri` tablosundan cari listeleme
  - Cari ekleme / güncelleme
  - Aktif-pasif filtreleme (son 90 gün sipariş hareketine göre)
  - Cari bazlı bakiye gösterimi (`Hareketler`)

- **Sipariş Yönetimi**
  - `Siparis` tablosundan sipariş oluşturma ve listeleme
  - Sipariş oluştururken cari, şantiye, reçete (`Recete`) ve hizmet (`Hizmet`) seçimi
  - Durum takibi: beklemede / üretimde / tamamlandı (`SiparisDurum`)
  - Siparişten üretime otomatik aktarım (`UretimPlan`)

- **Muhasebe Entegrasyonu**
  - Cari hareket kayıtları (`Hareketler`)
  - Ödeme / tahsilat giriş ekranı
  - Cari hesap hareketleri
  - Cari bazlı borç-alacak raporu
  - Excel/PDF dışa aktarım

- **Santral Entegrasyonu**
  - Üretim plan listesi ve durum yönetimi
  - Reçete bazlı üretim grafiği
  - Sol menü (muhasebe odaklı koyu-gri), sağda üretim akışı dashboard görünümü

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Uygulama varsayılan olarak aynı klasördeki `MCSSoft_New.sqlite` dosyasına bağlanır.

## Not

Uygulama ilk açıldığında aşağıdaki ek tablolar otomatik oluşturulur:

- `Hareketler`
- `SiparisDurum`
- `UretimPlan`

Bu tablolar, mevcut veritabanı yapısını bozmadan istenen modülleri tamamlamak için kullanılır.
