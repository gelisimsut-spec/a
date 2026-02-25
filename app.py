from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import and_, case, func

from database import Base, SessionLocal, engine
from models import Hareket, Hizmet, Musteri, Recete, Santiye, Siparis, SiparisDurum, UretimPlan

st.set_page_config(page_title="Beton Santrali Yönetim", layout="wide")


@st.cache_resource
def init_db():
    Base.metadata.create_all(bind=engine)


init_db()


DURUM_RENK = {
    "beklemede": "#f59e0b",
    "üretimde": "#22c55e",
    "tamamlandı": "#3b82f6",
}

st.markdown(
    """
    <style>
      .main {background-color: #f8fafc;}
      section[data-testid="stSidebar"] {background-color: #374151;}
      section[data-testid="stSidebar"] * {color: #f9fafb;}
      .santral-card {padding:10px;border-radius:8px;background:#ecfccb;border:1px solid #84cc16;}
    </style>
    """,
    unsafe_allow_html=True,
)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rapor")
    return out.getvalue()


def to_pdf_bytes(df: pd.DataFrame, title: str) -> bytes:
    out = BytesIO()
    pdf = canvas.Canvas(out, pagesize=A4)
    pdf.setTitle(title)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 810, title)
    pdf.setFont("Helvetica", 9)
    y = 790
    line = " | ".join(df.columns)
    pdf.drawString(40, y, line[:130])
    y -= 18
    for _, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values)
        pdf.drawString(40, y, text[:130])
        y -= 14
        if y < 40:
            pdf.showPage()
            y = 810
    pdf.save()
    return out.getvalue()


def cari_yonetimi(db):
    st.subheader("Cari Yönetimi")
    musteri_adet = db.query(func.count(Musteri.kod)).scalar()
    st.metric("Toplam Cari", musteri_adet)

    with st.expander("Yeni Cari Ekle", expanded=False):
        with st.form("cari_ekle"):
            ad = st.text_input("Firma Adı")
            vergi_no = st.text_input("Vergi No")
            telefon = st.text_input("Telefon")
            adres = st.text_area("Adres")
            vergi_dairesi = st.text_input("Vergi Dairesi")
            il = st.text_input("İl")
            ilce = st.text_input("İlçe")
            if st.form_submit_button("Kaydet"):
                db.add(
                    Musteri(
                        ad=ad,
                        vergi_numarasi=vergi_no,
                        telefon=telefon,
                        adres=adres,
                        vergi_dairesi=vergi_dairesi,
                        il=il,
                        ilce=ilce,
                    )
                )
                db.commit()
                st.success("Cari kaydedildi.")

    musteri_rows = db.query(Musteri).order_by(Musteri.ad.asc()).all()
    siparis_90 = {
        x[0]
        for x in db.query(Siparis.musteri)
        .filter(Siparis.tarih >= datetime.utcnow() - timedelta(days=90))
        .all()
    }

    filter_durum = st.selectbox("Cari Durumu", ["Tümü", "Aktif", "Pasif"])
    data = []
    for m in musteri_rows:
        aktif = m.ad in siparis_90
        bakiye = (
            db.query(
                func.coalesce(
                    func.sum(
                        case((Hareket.hareket_tipi == "BORC", Hareket.tutar), else_=0)
                    ),
                    0,
                )
                - func.coalesce(
                    func.sum(
                        case((Hareket.hareket_tipi == "ALACAK", Hareket.tutar), else_=0)
                    ),
                    0,
                )
            )
            .filter(Hareket.musteri_id == m.kod)
            .scalar()
        )
        if filter_durum == "Aktif" and not aktif:
            continue
        if filter_durum == "Pasif" and aktif:
            continue
        data.append(
            {
                "kod": m.kod,
                "firma": m.ad,
                "telefon": m.telefon,
                "vergi_no": m.vergi_numarasi,
                "aktif": "Aktif" if aktif else "Pasif",
                "bakiye": round(float(bakiye or 0), 2),
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, width="stretch")

    st.markdown("#### Cari Düzenleme")
    if musteri_rows:
        selected = st.selectbox("Cari", musteri_rows, format_func=lambda x: f"{x.kod} - {x.ad}")
        with st.form("cari_duzenle"):
            selected.ad = st.text_input("Firma Adı", value=selected.ad or "")
            selected.vergi_numarasi = st.text_input("Vergi No", value=selected.vergi_numarasi or "")
            selected.telefon = st.text_input("Telefon", value=selected.telefon or "")
            selected.adres = st.text_area("Adres", value=selected.adres or "")
            if st.form_submit_button("Güncelle"):
                db.commit()
                st.success("Cari güncellendi.")


def siparis_yonetimi(db):
    st.subheader("Sipariş Yönetimi")
    musteriler = db.query(Musteri).order_by(Musteri.ad.asc()).all()
    santiyeler = db.query(Santiye).order_by(Santiye.ad.asc()).all()
    receteler = db.query(Recete).order_by(Recete.ad.asc()).all()
    hizmetler = db.query(Hizmet).order_by(Hizmet.ad.asc()).all()

    with st.expander("Yeni Sipariş", expanded=True):
        with st.form("siparis_ekle"):
            ad = st.text_input("Sipariş Adı")
            musteri = st.selectbox("Cari", musteriler, format_func=lambda x: x.ad if x else "", index=None)
            santiye = st.selectbox("Şantiye", santiyeler, format_func=lambda x: x.ad if x else "", index=None)
            recete = st.selectbox("Reçete", receteler, format_func=lambda x: x.ad if x else "", index=None)
            hizmet = st.selectbox("Hizmet Türü", hizmetler, format_func=lambda x: x.ad if x else "", index=None)
            miktar = st.number_input("Miktar (m3)", min_value=0.0, step=1.0)
            durum = st.selectbox("Sipariş Durumu", ["beklemede", "üretimde", "tamamlandı"])
            if st.form_submit_button("Siparişi Oluştur"):
                s = Siparis(
                    ad=ad,
                    tarih=datetime.utcnow(),
                    musteri=(musteri.ad if musteri else None),
                    santiye=(santiye.ad if santiye else None),
                    recete=(recete.ad if recete else None),
                    hizmet=(hizmet.ad if hizmet else None),
                    miktar=str(miktar),
                    toplamMiktar=str(miktar),
                    tamamlandi=(durum == "tamamlandı"),
                )
                db.add(s)
                db.commit()
                db.refresh(s)
                db.add(SiparisDurum(siparis_id=s.kod, durum=durum))
                db.add(
                    UretimPlan(
                        siparis_id=s.kod,
                        recete_adi=s.recete,
                        planlanan_miktar=float(miktar),
                        uretilen_miktar=0,
                        durum=durum,
                    )
                )
                db.commit()
                st.success("Sipariş oluşturuldu ve üretim planına aktarıldı.")

    orders = (
        db.query(Siparis, SiparisDurum)
        .join(SiparisDurum, SiparisDurum.siparis_id == Siparis.kod, isouter=True)
        .order_by(Siparis.kod.desc())
        .all()
    )
    data = []
    for s, d in orders:
        data.append(
            {
                "siparis_no": s.kod,
                "ad": s.ad,
                "musteri": s.musteri,
                "recete": s.recete,
                "hizmet": s.hizmet,
                "miktar": s.miktar,
                "durum": d.durum if d else ("tamamlandı" if s.tamamlandi else "beklemede"),
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, width="stretch")

    st.markdown("#### Sipariş Detay ve Durum Güncelle")
    if orders:
        sip_ids = [s.kod for s, _ in orders]
        secilen_id = st.selectbox("Sipariş", sip_ids)
        secilen = next((pair for pair in orders if pair[0].kod == secilen_id), None)
        if secilen:
            s, d = secilen
            st.write({"müşteri": s.musteri, "şantiye": s.santiye, "pompa": s.pompa, "pompacı": s.pompaci})
            yeni_durum = st.selectbox("Yeni Durum", ["beklemede", "üretimde", "tamamlandı"], key="durum_upd")
            if st.button("Durumu Güncelle"):
                if d:
                    d.durum = yeni_durum
                else:
                    db.add(SiparisDurum(siparis_id=s.kod, durum=yeni_durum))
                s.tamamlandi = yeni_durum == "tamamlandı"
                plan = db.query(UretimPlan).filter(UretimPlan.siparis_id == s.kod).first()
                if plan:
                    plan.durum = yeni_durum
                    if yeni_durum == "tamamlandı":
                        plan.uretilen_miktar = plan.planlanan_miktar
                db.commit()
                st.success("Durum güncellendi.")


def muhasebe(db):
    st.subheader("Muhasebe Entegrasyonu")
    musteriler = db.query(Musteri).order_by(Musteri.ad.asc()).all()
    m = st.selectbox("Cari Seçimi", musteriler, format_func=lambda x: x.ad if x else "", index=None)

    if m:
        hereketler = db.query(Hareket).filter(Hareket.musteri_id == m.kod).order_by(Hareket.tarih.desc()).all()
        borc = sum(h.tutar for h in hereketler if h.hareket_tipi == "BORC")
        alacak = sum(h.tutar for h in hereketler if h.hareket_tipi == "ALACAK")
        st.metric("Bakiye", f"{(borc - alacak):,.2f} TL")

        with st.form("hareket_ekle"):
            tip = st.selectbox("İşlem Tipi", ["BORC", "ALACAK"])
            tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
            aciklama = st.text_input("Açıklama")
            if st.form_submit_button("Ödeme/Tahsilat Kaydet"):
                db.add(Hareket(musteri_id=m.kod, hareket_tipi=tip, tutar=tutar, aciklama=aciklama))
                db.commit()
                st.success("Hareket kaydedildi.")

        hdf = pd.DataFrame(
            [
                {
                    "tarih": h.tarih,
                    "tip": h.hareket_tipi,
                    "tutar": h.tutar,
                    "aciklama": h.aciklama,
                }
                for h in hereketler
            ]
        )
        st.dataframe(hdf, width="stretch")
        if not hdf.empty:
            st.download_button("Excel İndir", data=to_excel_bytes(hdf), file_name=f"{m.ad}_hareketler.xlsx")
            st.download_button("PDF İndir", data=to_pdf_bytes(hdf, f"{m.ad} hesap hareketleri"), file_name=f"{m.ad}_hareketler.pdf")

    st.markdown("#### Cari Bazlı Borç - Alacak Raporu")
    rapor = []
    for musteri in musteriler:
        hareketler = db.query(Hareket).filter(Hareket.musteri_id == musteri.kod).all()
        borc = sum(h.tutar for h in hareketler if h.hareket_tipi == "BORC")
        alacak = sum(h.tutar for h in hareketler if h.hareket_tipi == "ALACAK")
        rapor.append({"cari": musteri.ad, "borc": borc, "alacak": alacak, "bakiye": borc - alacak})
    rdf = pd.DataFrame(rapor)
    st.dataframe(rdf, width="stretch")


def santral_entegrasyonu(db):
    st.subheader("Beton Santrali Entegrasyonu")
    left, right = st.columns([1, 2])
    with left:
        st.markdown("<div class='santral-card'><b>Üretim Akışı</b><br/>Bekleyen -> Üretimde -> Tamamlandı</div>", unsafe_allow_html=True)
    with right:
        plans = db.query(UretimPlan).order_by(UretimPlan.plan_tarihi.desc()).all()
        df = pd.DataFrame(
            [
                {
                    "sipariş": p.siparis_id,
                    "reçete": p.recete_adi,
                    "planlanan": p.planlanan_miktar,
                    "üretilen": p.uretilen_miktar,
                    "durum": p.durum,
                }
                for p in plans
            ]
        )
        st.dataframe(df, width="stretch")

        st.markdown("#### Reçete Bazlı Üretim Raporu")
        if not df.empty:
            g = df.groupby("reçete", as_index=False)[["planlanan", "üretilen"]].sum()
            st.bar_chart(g.set_index("reçete"))


st.title("Beton Santrali + Muhasebe Yönetim Arayüzü")
modul = st.sidebar.radio(
    "Modüller",
    ["Cari Yönetimi", "Sipariş Yönetimi", "Muhasebe", "Santral Entegrasyonu"],
)

with SessionLocal() as db:
    if modul == "Cari Yönetimi":
        cari_yonetimi(db)
    elif modul == "Sipariş Yönetimi":
        siparis_yonetimi(db)
    elif modul == "Muhasebe":
        muhasebe(db)
    else:
        santral_entegrasyonu(db)
