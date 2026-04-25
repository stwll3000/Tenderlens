"""
SQLAlchemy модели для базы данных TenderLens.

Таблицы:
- regions: справочник регионов РФ
- customers: заказчики (организации)
- lots: лоты/закупки с zakupki.gov.ru
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    String,
    Float,
    DateTime,
    Integer,
    Text,
    Index,
    UniqueConstraint,
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
    )
    
    def __repr__(self) -> str:
        return f"<Lot(reg_number={self.reg_number}, price={self.initial_price})>"
