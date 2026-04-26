"""
SQLAlchemy модели для базы данных TenderLens.

Таблицы:
- regions: справочник регионов РФ
- customers: заказчики (организации)
- lots: лоты/закупки с zakupki.gov.ru
- suppliers: поставщики (юр. лица из протоколов)
- lot_participations: участие поставщика в конкретном лоте
- lot_categories: нормализованные категории лотов
- price_benchmarks: кэшированные benchmark'и по нише/региону/периоду
- lot_scores: результат скоринга лота (Profit Score)
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger,
    String,
    Float,
    DateTime,
    Date,
    Integer,
    Text,
    Index,
    UniqueConstraint,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class Region(Base):
    """Справочник регионов РФ."""
    
    __tablename__ = "regions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Region(code={self.code}, name={self.name})>"


class Customer(Base):
    """Заказчики (организации)."""
    
    __tablename__ = "customers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    # Для будущего расширения: ИНН, КПП, адрес из ЕГРЮЛ
    inn: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    kpp: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    # Дополнительные поля для customer health
    in_rnp: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_contracts_12m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_payment_delay_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<Customer(name={self.name[:50]}, inn={self.inn})>"


class Lot(Base):
    """Лоты/закупки с zakupki.gov.ru."""
    
    __tablename__ = "lots"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reg_number: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    law: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    purchase_method: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_name: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Связь с заказчиком
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    customer_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    
    # Финансовые данные
    initial_price: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    final_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_reduction_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # География
    region_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    region_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Даты закупки
    published_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    updated_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deadline_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # ОКПД2 коды (JSON array as string)
    okpd2_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Нормализованная ниша
    niche_slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Полный текст ТЗ для NLP анализа
    tz_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Конкуренция
    participants_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Метаданные
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # Составные индексы для аналитики
    __table_args__ = (
        Index('idx_region_law', 'region_code', 'law'),
        Index('idx_status_scraped', 'status', 'scraped_at'),
        Index('idx_customer_price', 'customer_url', 'initial_price'),
        Index('idx_niche_region', 'niche_slug', 'region_code'),
    )
    
    def __repr__(self) -> str:
        return f"<Lot(reg_number={self.reg_number}, price={self.initial_price})>"


class Supplier(Base):
    """Поставщики (юр. лица из протоколов)."""
    
    __tablename__ = "suppliers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inn: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kpp: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    region_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True, index=True)
    is_smp: Mapped[bool] = mapped_column(Boolean, default=False)  # СМП/СОНКО
    in_rnp: Mapped[bool] = mapped_column(Boolean, default=False)  # реестр недобросовестных
    rnp_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    egrul_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # выручка
    egrul_employees: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<Supplier(inn={self.inn}, name={self.name[:50]})>"


class LotParticipation(Base):
    """Участие поставщика в конкретном лоте (заявка)."""
    
    __tablename__ = "lot_participations"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lots.id"), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    bid_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # цена заявки
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # место в торгах
    rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('lot_id', 'supplier_id', name='uq_lot_supplier'),
        Index('idx_winner_lot', 'is_winner', 'lot_id'),
    )
    
    def __repr__(self) -> str:
        return f"<LotParticipation(lot_id={self.lot_id}, supplier_id={self.supplier_id}, winner={self.is_winner})>"


class LotCategory(Base):
    """Нормализованные категории лотов (наша таксономия поверх ОКПД2)."""
    
    __tablename__ = "lot_categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    okpd2_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    niche_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('okpd2_prefix', 'niche_slug', name='uq_okpd2_niche'),
    )
    
    def __repr__(self) -> str:
        return f"<LotCategory(niche_slug={self.niche_slug}, okpd2={self.okpd2_prefix})>"


class PriceBenchmark(Base):
    """Кэшированные benchmark'и по нише/региону/периоду."""
    
    __tablename__ = "price_benchmarks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    niche_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    median_initial_price: Mapped[float] = mapped_column(Float, nullable=False)
    median_final_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_alpha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # медианное снижение
    avg_unique_suppliers: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_niche_region_period', 'niche_slug', 'region_code', 'period_end'),
    )
    
    def __repr__(self) -> str:
        return f"<PriceBenchmark(niche={self.niche_slug}, region={self.region_code}, median={self.median_initial_price})>"


class LotScore(Base):
    """Результат скоринга лота (Profit Score)."""
    
    __tablename__ = "lot_scores"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lots.id"), nullable=False, unique=True, index=True)
    profit_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)  # 0..100
    margin_signal: Mapped[float] = mapped_column(Float, nullable=False)  # компонент A
    competition_signal: Mapped[float] = mapped_column(Float, nullable=False)  # B
    captive_signal: Mapped[float] = mapped_column(Float, nullable=False)  # C
    timing_signal: Mapped[float] = mapped_column(Float, nullable=False)  # D
    spec_purity_signal: Mapped[float] = mapped_column(Float, nullable=False)  # E
    customer_health: Mapped[float] = mapped_column(Float, nullable=False)  # F
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default='[]')  # ["captive", "premium_nmc", ...]
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<LotScore(lot_id={self.lot_id}, score={self.profit_score})>"
