from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Musteri(Base):
    __tablename__ = "Musteri"

    kod = Column(Integer, primary_key=True, index=True)
    ad = Column(Text)
    telefon = Column(Text)
    fax = Column(Text)
    adres = Column(Text)
    vergi_dairesi = Column(Text)
    vergi_numarasi = Column(Text)
    il = Column(Text)
    ilce = Column(Text)


class Siparis(Base):
    __tablename__ = "Siparis"

    kod = Column(Integer, primary_key=True, index=True)
    ad = Column(Text)
    tarih = Column(DateTime)
    musteri = Column(Text)
    santiye = Column(Text)
    recete = Column(Text)
    hizmet = Column(Text)
    pompa = Column(Text)
    pompaci = Column(Text)
    miktar = Column(Text)
    toplamMiktar = Column(Text)
    tamamlandi = Column(Boolean, default=False)


class Recete(Base):
    __tablename__ = "Recete"

    kod = Column(Integer, primary_key=True, index=True)
    ad = Column(Text)
    beton_sinifi = Column(Text)
    recete_sinifi = Column(Text)


class Hizmet(Base):
    __tablename__ = "Hizmet"

    kod = Column(Integer, primary_key=True, index=True)
    ad = Column(Text)


class Santiye(Base):
    __tablename__ = "Santiye"

    kod = Column(Integer, primary_key=True, index=True)
    ad = Column(Text)
    musteri_adi = Column(Text)


class Hareket(Base):
    __tablename__ = "Hareketler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    musteri_id = Column(Integer, ForeignKey("Musteri.kod"), nullable=False)
    hareket_tipi = Column(String(20), nullable=False)  # BORC / ALACAK
    tutar = Column(Float, nullable=False)
    aciklama = Column(Text)
    tarih = Column(DateTime, default=datetime.utcnow)

    musteri = relationship("Musteri")


class SiparisDurum(Base):
    __tablename__ = "SiparisDurum"

    id = Column(Integer, primary_key=True, autoincrement=True)
    siparis_id = Column(Integer, ForeignKey("Siparis.kod"), nullable=False, unique=True)
    durum = Column(String(20), nullable=False, default="beklemede")
    guncelleme_tarihi = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    siparis = relationship("Siparis")


class UretimPlan(Base):
    __tablename__ = "UretimPlan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    siparis_id = Column(Integer, ForeignKey("Siparis.kod"), nullable=False, unique=True)
    recete_adi = Column(Text)
    planlanan_miktar = Column(Float, default=0)
    uretilen_miktar = Column(Float, default=0)
    durum = Column(String(20), default="beklemede")
    plan_tarihi = Column(DateTime, default=datetime.utcnow)

    siparis = relationship("Siparis")
