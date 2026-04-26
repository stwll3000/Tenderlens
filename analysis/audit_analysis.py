"""
TenderLens — Comprehensive Audit-Based Data Analysis
=====================================================
Generates synthetic data matching the project schema and performs
a thorough analysis based on the TenderLens Analytics Audit.
"""

import pandas as pd
import numpy as np
import json
import re
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

np.random.seed(42)

# ============================================================
# 1. GENERATE REALISTIC SYNTHETIC DATA
# ============================================================

REGIONS = {
    "54": "Новосибирская область",
    "77": "Москва",
    "50": "Московская область",
}

STATUSES = [
    "Подача заявок",
    "Определение поставщика завершено",
    "Работа комиссии",
    "Закупка завершена",
    "Закупка отменена",
]
STATUS_WEIGHTS = [0.52, 0.37, 0.05, 0.03, 0.03]

PURCHASE_METHODS = [
    "Электронный аукцион",
    "Запрос котировок в электронной форме",
    "Открытый конкурс в электронной форме",
    "Закупка у единственного поставщика",
    "Конкурс с ограниченным участием",
]
METHOD_WEIGHTS = [0.45, 0.25, 0.12, 0.13, 0.05]

CUSTOMERS = [
    "ГБУЗ НСО «Городская клиническая больница №1»",
    "ФГБОУ ВО «Московский государственный университет»",
    "ГКУ МО «Дирекция дорожного строительства»",
    "ГБУЗ «НИИ скорой помощи им. Н.В. Склифосовского»",
    "МБУ «Управление дорожного хозяйства»",
    "ГБОУ «Школа №1234»",
    "ГУП «Мосводоканал»",
    "ФГБУ «НМИЦ хирургии им. А.В. Вишневского»",
    "АО «Новосибирский завод химконцентратов»",
    "МУП «Водоканал» г. Новосибирска",
    "ГБУЗ МО «Московская областная больница»",
    "ФГАОУ ВО «НГУ»",
    "ООО «Газпром трансгаз Москва»",
    "ГАУ НСО «Центр спортивной подготовки»",
    "ГБОУ ВО МО «Академия социального управления»",
    "ФКУЗ «МСЧ МВД России по г. Москве»",
    "ГБУЗ «ГКБ №67 им. Л.А. Ворохобова»",
    "АО «Мосинжпроект»",
    "МКУ «Управление капитального строительства»",
    "ПАО «Россети Московский регион»",
    "ГБОУ Школа №2120",
    "ФГБУ «ЦИТО им. Н.Н. Приорова»",
    "МБУ «Новосибирский зоопарк»",
    "ГКУ «Организатор перевозок»",
    "ФГУП «Охрана» Росгвардии",
    "ГБУ «Жилищник района Хамовники»",
    "ГУП МО «МОСТРАНСАВТО»",
    "ГБУЗ «Детская городская больница №9 им. Г.Н. Сперанского»",
    "МУП «Горводоканал»",
    "ФГБНУ «НИИ нормальной физиологии»",
]

OBJECT_NAMES_TEMPLATES = [
    "Поставка медицинских расходных материалов для нужд {customer}",
    "Поставка канцелярских товаров и бумаги формата А4",
    "Оказание услуг по уборке территорий и помещений",
    "Поставка средств индивидуальной защиты (СИЗ)",
    "Поставка компьютерного оборудования и оргтехники",
    "Выполнение работ по текущему ремонту помещений",
    "Оказание услуг по техническому обслуживанию лифтов",
    "Поставка продуктов питания для организации питания",
    "Поставка лекарственных препаратов",
    "Оказание услуг по охране объектов",
    "Поставка мебели для оснащения учебных кабинетов",
    "Выполнение работ по капитальному ремонту кровли",
    "Оказание транспортных услуг для перевозки грузов",
    "Поставка спецодежды и рабочей обуви",
    "Оказание услуг по обслуживанию IT-инфраструктуры",
    "Поставка хозяйственных товаров и моющих средств",
    "Выполнение работ по благоустройству территории",
    "Поставка медицинского оборудования (опыт не менее 5 лет работы с аналогичным оборудованием)",
    "Поставка оборудования производителя Siemens Healthineers, эквивалент не допускается",
    "Оказание услуг по содержанию автомобильных дорог (наличие свидетельства СРО)",
    "Поставка лазерных картриджей конкретной модели HP 26A CF226A",
    "Выполнение проектно-изыскательских работ (исполнитель должен находиться в Московской области)",
]

OKPD2_CODES_BY_TYPE = {
    "med": ["32.50.13", "32.50.21", "32.50.41", "21.20.10"],
    "kanc": ["17.23.13", "32.99.12"],
    "klining": ["81.21.10", "81.22.12"],
    "siz": ["14.12.10", "32.99.11"],
    "it": ["26.20.11", "27.20.21", "26.20.40"],
    "remont": ["41.20.40", "43.31.10"],
    "lift": ["33.12.19"],
    "pitanie": ["10.11.10", "10.51.40"],
    "lekarstva": ["21.20.10", "21.20.23"],
    "ohrana": ["80.10.12"],
    "mebel": ["31.01.11", "31.09.12"],
    "krovlya": ["43.91.11"],
    "transport": ["49.41.11"],
    "specodezhda": ["14.12.10", "15.20.31"],
    "it_service": ["62.09.20", "95.11.10"],
    "hoztovary": ["20.41.31", "20.41.32"],
    "blagoustr": ["81.30.10"],
}

def generate_lots(n=150):
    """Generate n realistic lot records."""
    lots = []
    base_date = datetime(2026, 1, 25)
    end_date = datetime(2026, 4, 25)
    date_range_days = (end_date - base_date).days
    
    region_codes = list(REGIONS.keys())
    region_weights = [0.33, 0.34, 0.33]  # roughly equal
    
    for i in range(n):
        region_code = np.random.choice(region_codes, p=region_weights)
        region_name = REGIONS[region_code]
        
        status = np.random.choice(STATUSES, p=STATUS_WEIGHTS)
        law = np.random.choice(["44-ФЗ", "223-ФЗ"], p=[0.83, 0.17])
        purchase_method = np.random.choice(PURCHASE_METHODS, p=METHOD_WEIGHTS)
        customer = np.random.choice(CUSTOMERS)
        
        # Price: log-normal distribution matching described stats
        # median ~1.17M, mean ~39.5M, max ~986M
        log_price = np.random.normal(14.0, 2.5)  # ln(1.2M) ≈ 14.0
        initial_price = max(3000, min(1_000_000_000, np.exp(log_price)))
        
        # Dates
        pub_offset = np.random.randint(0, date_range_days)
        pub_date = base_date + timedelta(days=pub_offset)
        deadline_days = np.random.choice(
            [3, 5, 7, 10, 14, 21, 30, 45],
            p=[0.05, 0.10, 0.20, 0.25, 0.20, 0.10, 0.07, 0.03]
        )
        deadline_date = pub_date + timedelta(days=int(deadline_days))
        
        # Object name and OKPD2
        obj_idx = np.random.randint(0, len(OBJECT_NAMES_TEMPLATES))
        object_name = OBJECT_NAMES_TEMPLATES[obj_idx].format(customer=customer[:30])
        
        # Pick OKPD2 codes
        category_keys = list(OKPD2_CODES_BY_TYPE.keys())
        cat = np.random.choice(category_keys)
        okpd2 = json.dumps(OKPD2_CODES_BY_TYPE[cat][:np.random.randint(1, 3)])
        
        # final_price and participants_count: mostly NULL as per audit
        final_price = None
        price_reduction_pct = None
        participants_count = None
        
        if status == "Определение поставщика завершено":
            # ~30% chance of having final_price even when completed
            if np.random.random() < 0.30:
                reduction = np.random.uniform(0.01, 0.35)
                final_price = round(initial_price * (1 - reduction), 2)
                price_reduction_pct = round(reduction * 100, 2)
            # ~40% chance of having participants_count
            if np.random.random() < 0.40:
                participants_count = max(1, int(np.random.lognormal(1.0, 0.7)))
        elif status == "Закупка завершена":
            if np.random.random() < 0.25:
                reduction = np.random.uniform(0.01, 0.30)
                final_price = round(initial_price * (1 - reduction), 2)
                price_reduction_pct = round(reduction * 100, 2)
            if np.random.random() < 0.35:
                participants_count = max(1, int(np.random.lognormal(1.0, 0.7)))
        
        lot = {
            "reg_number": f"0{region_code}{np.random.randint(1000000, 9999999)}",
            "url": f"https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber=0{region_code}{np.random.randint(1000000, 9999999)}",
            "law": law,
            "purchase_method": purchase_method,
            "status": status,
            "object_name": object_name,
            "customer_name": customer,
            "customer_url": f"https://zakupki.gov.ru/epz/organization/view/general.html?orgId={np.random.randint(100000, 999999)}",
            "initial_price": round(initial_price, 2),
            "final_price": final_price,
            "price_reduction_pct": price_reduction_pct,
            "region_code": region_code,
            "region_name": region_name,
            "published_date": pub_date.strftime("%d.%m.%Y"),
            "updated_date": (pub_date + timedelta(days=np.random.randint(0, 5))).strftime("%d.%m.%Y"),
            "deadline_date": deadline_date.strftime("%d.%m.%Y"),
            "okpd2_codes": okpd2,
            "participants_count": participants_count,
            "scraped_at": datetime.now().isoformat(),
        }
        lots.append(lot)
    
    return lots

def main():
    # Generate data
    lots_data = generate_lots(150)
    
    # Save to data/
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    json_path = data_dir / "lots_synthetic_150_audit.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(lots_data, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(lots_data)} synthetic lots -> {json_path}")
    
    # Load into DataFrame
    df = pd.DataFrame(lots_data)
    df["initial_price"] = pd.to_numeric(df["initial_price"], errors="coerce")
    df["final_price"] = pd.to_numeric(df["final_price"], errors="coerce")
    df["participants_count"] = pd.to_numeric(df["participants_count"], errors="coerce")
    
    # Save CSV summary
    csv_path = data_dir / "lots_synthetic_summary.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"Saved CSV summary -> {csv_path}")
    
    return df

if __name__ == "__main__":
    df = main()
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSample row:\n{df.iloc[0].to_dict()}")
