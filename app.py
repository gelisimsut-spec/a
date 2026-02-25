from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import case, func

from database import Base, SessionLocal, engine
from models import Hareket, Hizmet, Musteri, Recete, Santiye, Siparis, SiparisDurum, UretimPlan

st.set_page_config(page_title="MCS Beton Operasyon Merkezi", page_icon="🏗️", layout="wide")


@st.cache_resource
def init_db():
    Base.metadata.create_all(bind=engine)


init_db()

DURUM_RENK = {
    "beklemede": "#f59e0b",
    "üretimde": "#10b981",
    "tamamlandı": "#3b82f6",
}

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f3f6fb 0%, #eef2f7 100%); }
    section[data-testid="stSidebar"] {
      background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
      border-right: 1px solid #374151;
    }
    section[data-testid="stSidebar"] * { color: #f9fafb; }
    .header-card {
      background: linear-gradient(135deg, #0f766e, #2563eb);
      border-radius: 14px;
      color: white;
      padding: 18px 22px;
      margin-bottom: 16px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
    }
    .metric-card {
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 12px;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 2px 10px;
      color: white;
      font-size: 12px;
      font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="header-card">
            <h2 style="margin:0;">{title}</h2>
            <p style="margin:4px 0 0 0; opacity:.92;">{subtitle}</p>
        </div>
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
    pdf.drawString(40, y, " | ".join(df.columns)[:130])
    y -= 18
    for _, row in df.iterrows():
        pdf.drawString(40, y, " | ".join(str(v) for v in row.values)[:130])
        y -= 14
        if y < 40:
            pdf.showPage()
            y = 810
    pdf.save()
    return out.getvalue()


def musteri_bakiye(db, musteri_id: int) -> float:
    borc = db.query(func.coalesce(func.sum(case((Hareket.hareket_tipi == "BORC", Hareket.tutar), else_=0)), 0)).filter(
        Hareket.musteri_id == musteri_id
    ).scalar()
    alacak = db.query(func.coalesce(func.sum(case((Hareket.hareket_tipi == "ALACAK", Hareket.tutar), else_=0)), 0)).filter(
        Hareket.musteri_id == musteri_id
    ).scalar()
    return float((borc or 0) - (alacak or 0))


def dashboard(db):
    show_header("Operasyon Dashboard", "Muhasebe ve üretim akışını aynı ekranda izleyin.")
    total_cari = db.query(func.count(Musteri.kod)).scalar() or 0
    total_siparis = db.query(func.count(Siparis.kod)).scalar() or 0
    aktif_siparis = (
        db.query(func.count(SiparisDurum.id))
        .filter(SiparisDurum.durum.in_(["beklemede", "üretimde"]))
        .scalar()
        or 0
    )
    tamamlanan = db.query(func.count(SiparisDurum.id)).filter(SiparisDurum.durum == "tamamlandı").scalar() or 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Cari", total_cari)
    m2.metric("Toplam Sipariş", total_siparis)
    m3.metric("Açık Sipariş", aktif_siparis)
    m4.metric("Tamamlanan", tamamlanan)

    left, right = st.columns([1.2, 1.8])
    with left:
        st.markdown("### Son Siparişler")
        rows = (
            db.query(Siparis, SiparisDurum)
            .join(SiparisDurum, SiparisDurum.siparis_id == Siparis.kod, isouter=True)
            .order_by(Siparis.kod.desc())
            .limit(8)
            .all()
        )
        for sip, durum in rows:
            d = durum.durum if durum else ("tamamlandı" if sip.tamamlandi else "beklemede")
            renk = DURUM_RENK.get(d, "#6b7280")
            st.markdown(
                f"""
                <div class='metric-card' style='margin-bottom:8px;'>
                  <b>#{sip.kod} - {sip.ad or '-'} </b><br/>
                  <span>{sip.musteri or '-'}</span> · <span>{sip.recete or '-'}</span><br/>
                  <span class='pill' style='background:{renk}; margin-top:6px;'>{d}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with right:
        st.markdown("### Reçete Bazlı Plan / Üretim")
        plans = db.query(UretimPlan).all()
        pdf = pd.DataFrame(
            [
                {"reçete": p.recete_adi or "Belirtilmedi", "planlanan": p.planlanan_miktar, "üretilen": p.uretilen_miktar}
                for p in plans
            ]
        )
        if pdf.empty:
            st.info("Henüz üretim planı bulunmuyor.")
        else:
            grouped = pdf.groupby("reçete", as_index=False)[["planlanan", "üretilen"]].sum()
            st.bar_chart(grouped.set_index("reçete"), height=340)


def cari_yonetimi(db):
    show_header("Cari Yönetimi", "Cari açma, düzenleme, aktif/pasif takibi ve bakiye yönetimi")

    musteriler = db.query(Musteri).order_by(Musteri.ad.asc()).all()
    siparis_90 = {
        x[0]
        for x in db.query(Siparis.musteri).filter(Siparis.tarih >= datetime.utcnow() - timedelta(days=90)).all()
    }

    form_col, list_col = st.columns([1, 1.6])
    with form_col:
        st.markdown("#### Yeni Cari")
        with st.form("cari_ekle", clear_on_submit=True):
            ad = st.text_input("Firma Adı *")
            vergi_no = st.text_input("Vergi No")
            vergi_dairesi = st.text_input("Vergi Dairesi")
            telefon = st.text_input("Telefon")
            adres = st.text_area("Adres", height=90)
            il = st.text_input("İl")
            ilce = st.text_input("İlçe")
            if st.form_submit_button("Cari Kaydet", use_container_width=True):
                if not ad:
                    st.error("Firma adı zorunludur.")
                else:
                    db.add(
                        Musteri(
                            ad=ad,
                            vergi_numarasi=vergi_no,
                            vergi_dairesi=vergi_dairesi,
                            telefon=telefon,
                            adres=adres,
                            il=il,
                            ilce=ilce,
                        )
                    )
                    db.commit()
                    st.success("Cari kaydedildi.")

        st.markdown("#### Cari Düzenleme")
        if musteriler:
            selected = st.selectbox("Düzenlenecek Cari", musteriler, format_func=lambda x: f"{x.kod} - {x.ad}")
            with st.form("cari_guncelle"):
                selected.ad = st.text_input("Firma Adı", selected.ad or "")
                selected.vergi_numarasi = st.text_input("Vergi No", selected.vergi_numarasi or "")
                selected.telefon = st.text_input("Telefon", selected.telefon or "")
                selected.adres = st.text_area("Adres", selected.adres or "", height=80)
                if st.form_submit_button("Güncelle", use_container_width=True):
                    db.commit()
                    st.success("Cari güncellendi.")

    with list_col:
        st.markdown("#### Cari Listesi")
        filter_durum = st.segmented_control("Durum Filtresi", ["Tümü", "Aktif", "Pasif"], default="Tümü")
        rows = []
        for m in musteriler:
            aktif = (m.ad or "") in siparis_90
            if filter_durum == "Aktif" and not aktif:
                continue
            if filter_durum == "Pasif" and aktif:
                continue
            rows.append(
                {
                    "Kod": m.kod,
                    "Firma": m.ad,
                    "Telefon": m.telefon,
                    "Vergi No": m.vergi_numarasi,
                    "Durum": "Aktif" if aktif else "Pasif",
                    "Bakiye (TL)": round(musteri_bakiye(db, m.kod), 2),
                }
            )
        cdf = pd.DataFrame(rows)
        st.dataframe(cdf, width="stretch", height=470)


def siparis_yonetimi(db):
    show_header("Sipariş Yönetimi", "Cari, reçete ve hizmet seçimi ile sipariş ve durum takibi")
    musteriler = db.query(Musteri).order_by(Musteri.ad.asc()).all()
    santiyeler = db.query(Santiye).order_by(Santiye.ad.asc()).all()
    receteler = db.query(Recete).order_by(Recete.ad.asc()).all()
    hizmetler = db.query(Hizmet).order_by(Hizmet.ad.asc()).all()

    left, right = st.columns([1.1, 1.4])
    with left:
        st.markdown("#### Yeni Sipariş")
        with st.form("siparis_ekle", clear_on_submit=True):
            ad = st.text_input("Sipariş Adı *")
            musteri = st.selectbox("Cari", musteriler, format_func=lambda x: x.ad, index=None)
            santiye = st.selectbox("Şantiye", santiyeler, format_func=lambda x: x.ad, index=None)
            recete = st.selectbox("Reçete", receteler, format_func=lambda x: x.ad, index=None)
            hizmet = st.selectbox("Hizmet Türü", hizmetler, format_func=lambda x: x.ad, index=None)
            miktar = st.number_input("Miktar (m³)", min_value=0.0, step=1.0)
            durum = st.selectbox("Başlangıç Durumu", ["beklemede", "üretimde", "tamamlandı"])
            if st.form_submit_button("Sipariş Oluştur", use_container_width=True):
                if not ad or not musteri or not recete:
                    st.error("Sipariş adı, cari ve reçete alanları zorunludur.")
                else:
                    siparis = Siparis(
                        ad=ad,
                        tarih=datetime.utcnow(),
                        musteri=musteri.ad,
                        santiye=santiye.ad if santiye else None,
                        recete=recete.ad,
                        hizmet=hizmet.ad if hizmet else None,
                        miktar=str(miktar),
                        toplamMiktar=str(miktar),
                        tamamlandi=(durum == "tamamlandı"),
                    )
                    db.add(siparis)
                    db.commit()
                    db.refresh(siparis)
                    db.add(SiparisDurum(siparis_id=siparis.kod, durum=durum))
                    db.add(
                        UretimPlan(
                            siparis_id=siparis.kod,
                            recete_adi=siparis.recete,
                            planlanan_miktar=float(miktar),
                            uretilen_miktar=float(miktar if durum == "tamamlandı" else 0),
                            durum=durum,
                        )
                    )
                    db.commit()
                    st.success("Sipariş oluşturuldu, üretim planına otomatik aktarıldı.")

    with right:
        st.markdown("#### Sipariş Listesi")
        orders = (
            db.query(Siparis, SiparisDurum)
            .join(SiparisDurum, SiparisDurum.siparis_id == Siparis.kod, isouter=True)
            .order_by(Siparis.kod.desc())
            .all()
        )
        order_rows = []
        for s, d in orders:
            status = d.durum if d else ("tamamlandı" if s.tamamlandi else "beklemede")
            order_rows.append(
                {
                    "No": s.kod,
                    "Sipariş": s.ad,
                    "Cari": s.musteri,
                    "Şantiye": s.santiye,
                    "Reçete": s.recete,
                    "Hizmet": s.hizmet,
                    "Miktar": s.miktar,
                    "Durum": status,
                }
            )
        odf = pd.DataFrame(order_rows)
        st.dataframe(odf, width="stretch", height=350)

        if orders:
            st.markdown("#### Sipariş Detay / Durum Güncelle")
            sid = st.selectbox("Sipariş Numarası", [s.kod for s, _ in orders])
            order_pair = next((x for x in orders if x[0].kod == sid), None)
            if order_pair:
                s, d = order_pair
                detail_cols = st.columns(3)
                detail_cols[0].metric("Cari", s.musteri or "-")
                detail_cols[1].metric("Reçete", s.recete or "-")
                detail_cols[2].metric("Miktar", s.miktar or "0")

                new_status = st.select_slider("Durum", options=["beklemede", "üretimde", "tamamlandı"])
                if st.button("Durumu Kaydet", use_container_width=True):
                    if d:
                        d.durum = new_status
                    else:
                        db.add(SiparisDurum(siparis_id=s.kod, durum=new_status))
                    s.tamamlandi = new_status == "tamamlandı"
                    plan = db.query(UretimPlan).filter(UretimPlan.siparis_id == s.kod).first()
                    if plan:
                        plan.durum = new_status
                        if new_status == "tamamlandı":
                            plan.uretilen_miktar = plan.planlanan_miktar
                    db.commit()
                    st.success("Sipariş durumu güncellendi.")


def muhasebe(db):
    show_header("Muhasebe", "Cari bakiyeleri, ödeme/tahsilat girişleri ve borç-alacak raporları")
    musteriler = db.query(Musteri).order_by(Musteri.ad.asc()).all()

    left, right = st.columns([1, 1.8])
    with left:
        secilen = st.selectbox("Cari Seçimi", musteriler, format_func=lambda x: x.ad, index=None)
        if secilen:
            hareketler = db.query(Hareket).filter(Hareket.musteri_id == secilen.kod).order_by(Hareket.tarih.desc()).all()
            borc = sum(h.tutar for h in hareketler if h.hareket_tipi == "BORC")
            alacak = sum(h.tutar for h in hareketler if h.hareket_tipi == "ALACAK")
            st.metric("Cari Bakiye", f"{(borc - alacak):,.2f} TL")

            with st.form("hareket_ekle"):
                tip = st.radio("İşlem Tipi", ["BORC", "ALACAK"], horizontal=True)
                tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
                aciklama = st.text_input("Açıklama")
                if st.form_submit_button("Kaydet", use_container_width=True):
                    db.add(Hareket(musteri_id=secilen.kod, hareket_tipi=tip, tutar=tutar, aciklama=aciklama))
                    db.commit()
                    st.success("İşlem kaydedildi.")

    with right:
        st.markdown("#### Cari Hesap Hareketleri")
        if secilen:
            hereketler = db.query(Hareket).filter(Hareket.musteri_id == secilen.kod).order_by(Hareket.tarih.desc()).all()
            hdf = pd.DataFrame(
                [
                    {
                        "Tarih": h.tarih,
                        "Tip": h.hareket_tipi,
                        "Tutar": h.tutar,
                        "Açıklama": h.aciklama,
                    }
                    for h in hereketler
                ]
            )
            st.dataframe(hdf, width="stretch", height=300)
            if not hdf.empty:
                dl1, dl2 = st.columns(2)
                dl1.download_button("Excel İndir", data=to_excel_bytes(hdf), file_name=f"{secilen.ad}_hareketler.xlsx", use_container_width=True)
                dl2.download_button("PDF İndir", data=to_pdf_bytes(hdf, f"{secilen.ad} hareketleri"), file_name=f"{secilen.ad}_hareketler.pdf", use_container_width=True)

        st.markdown("#### Cari Bazlı Borç - Alacak")
        rapor = []
        for m in musteriler:
            hareketler = db.query(Hareket).filter(Hareket.musteri_id == m.kod).all()
            borc = sum(h.tutar for h in hareketler if h.hareket_tipi == "BORC")
            alacak = sum(h.tutar for h in hareketler if h.hareket_tipi == "ALACAK")
            rapor.append({"Cari": m.ad, "Borç": borc, "Alacak": alacak, "Bakiye": borc - alacak})
        rdf = pd.DataFrame(rapor)
        st.dataframe(rdf, width="stretch", height=220)


def santral_entegrasyonu(db):
    show_header("Santral Entegrasyonu", "Siparişten üretime otomatik akış, reçete bazlı planlama ve raporlama")
    plans = db.query(UretimPlan).order_by(UretimPlan.plan_tarihi.desc()).all()

    if not plans:
        st.info("Henüz üretim planı oluşturulmadı.")
        return

    p_df = pd.DataFrame(
        [
            {
                "Sipariş": p.siparis_id,
                "Reçete": p.recete_adi,
                "Planlanan": p.planlanan_miktar,
                "Üretilen": p.uretilen_miktar,
                "Durum": p.durum,
                "Plan Tarihi": p.plan_tarihi,
            }
            for p in plans
        ]
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Plan", len(p_df))
    c2.metric("Planlanan Üretim", f"{p_df['Planlanan'].sum():,.1f} m³")
    c3.metric("Gerçekleşen Üretim", f"{p_df['Üretilen'].sum():,.1f} m³")

    left, right = st.columns([1.2, 1.4])
    with left:
        st.markdown("#### Üretim Akış Tablosu")
        st.dataframe(p_df, width="stretch", height=380)
    with right:
        st.markdown("#### Reçete Bazlı Üretim")
        g = p_df.groupby("Reçete", as_index=False)[["Planlanan", "Üretilen"]].sum()
        st.bar_chart(g.set_index("Reçete"), height=320)
        st.markdown("#### Akış Durumları")
        durum_counts = p_df["Durum"].value_counts().reset_index()
        durum_counts.columns = ["Durum", "Adet"]
        st.dataframe(durum_counts, width="stretch")


st.sidebar.markdown("## 🧭 Modüller")
module = st.sidebar.radio(
    "Gezinme",
    ["Dashboard", "Cari Yönetimi", "Sipariş Yönetimi", "Muhasebe", "Santral Entegrasyonu"],
)
st.sidebar.caption("MCS Beton Operasyon Merkezi • v2")

with SessionLocal() as db:
    if module == "Dashboard":
        dashboard(db)
    elif module == "Cari Yönetimi":
        cari_yonetimi(db)
    elif module == "Sipariş Yönetimi":
        siparis_yonetimi(db)
    elif module == "Muhasebe":
        muhasebe(db)
    else:
        santral_entegrasyonu(db)
