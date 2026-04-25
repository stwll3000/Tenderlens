"""
TenderLens — Аналитический дашборд рынка госзакупок.

Streamlit приложение для визуализации и анализа данных о государственных закупках.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import json
from datetime import datetime

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent.parent))

from analytics import pricing, competition


# Конфигурация страницы
st.set_page_config(
    page_title="TenderLens — Аналитика госзакупок",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def load_data() -> pd.DataFrame:
    """Загрузка данных из JSON файла."""
    data_dir = Path(__file__).parent.parent / "data"
    
    # Ищем последний файл с данными
    json_files = sorted(data_dir.glob("lots_all_*.json"), reverse=True)
    
    if not json_files:
        st.error("Файлы с данными не найдены в директории data/")
        return pd.DataFrame()
    
    latest_file = json_files[0]
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df['initial_price'] = pd.to_numeric(df['initial_price'], errors='coerce')
    
    # Очистка данных
    df = df.dropna(subset=['region_name', 'initial_price'])
    
    return df


def format_price(price: float) -> str:
    """Форматирование цены с разделителями."""
    return f"{price:,.0f}".replace(",", " ") + " ₽"


def main():
    """Главная функция дашборда."""
    
    # Заголовок
    st.title("📊 TenderLens — Аналитика госзакупок")
    st.markdown("Платформа для анализа рынка государственных закупок России")
    
    # Загрузка данных
    with st.spinner("Загрузка данных..."):
        df = load_data()
    
    if df.empty:
        st.stop()
    
    # Боковая панель с фильтрами
    st.sidebar.header("🔍 Фильтры")
    
    # Фильтр по регионам
    unique_regions = df['region_name'].dropna().unique().tolist()
    regions = ["Все регионы"] + sorted([str(r) for r in unique_regions])
    selected_region = st.sidebar.selectbox("Регион", regions)
    
    # Фильтр по законам
    unique_laws = df['law'].dropna().unique().tolist()
    laws = ["Все законы"] + sorted([str(l) for l in unique_laws])
    selected_law = st.sidebar.selectbox("Закон", laws)
    
    # Фильтр по диапазону цен
    min_price = float(df['initial_price'].min())
    max_price = float(df['initial_price'].max())
    
    price_range = st.sidebar.slider(
        "Диапазон цен (₽)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price),
        format="%.0f"
    )
    
    # Фильтр по статусам
    unique_statuses = df['status'].dropna().unique().tolist()
    statuses = ["Все статусы"] + sorted([str(s) for s in unique_statuses])
    selected_status = st.sidebar.selectbox("Статус закупки", statuses)
    
    # Применение фильтров
    filtered_df = df.copy()
    
    if selected_region != "Все регионы":
        filtered_df = filtered_df[filtered_df['region_name'] == selected_region]
    
    if selected_law != "Все законы":
        filtered_df = filtered_df[filtered_df['law'] == selected_law]
    
    filtered_df = filtered_df[
        (filtered_df['initial_price'] >= price_range[0]) &
        (filtered_df['initial_price'] <= price_range[1])
    ]
    
    if selected_status != "Все статусы":
        filtered_df = filtered_df[filtered_df['status'] == selected_status]
    
    # Основные метрики
    st.header("📈 Основные показатели")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Всего лотов",
            f"{len(filtered_df):,}".replace(",", " "),
            delta=f"{len(filtered_df) - len(df)}" if len(filtered_df) != len(df) else None
        )
    
    with col2:
        total_volume = filtered_df['initial_price'].sum()
        st.metric(
            "Общий объём",
            format_price(total_volume)
        )
    
    with col3:
        avg_price = filtered_df['initial_price'].mean()
        st.metric(
            "Средняя цена",
            format_price(avg_price)
        )
    
    with col4:
        unique_customers = filtered_df['customer_name'].nunique()
        st.metric(
            "Заказчиков",
            f"{unique_customers:,}".replace(",", " ")
        )
    
    # Вкладки для разных разделов
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Анализ цен",
        "🏆 Конкуренция",
        "📊 Распределения",
        "📋 Данные"
    ])
    
    # Вкладка 1: Анализ цен
    with tab1:
        st.subheader("Статистика цен")
        
        # Используем модуль pricing
        price_dist = pricing.analyze_price_distribution(filtered_df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Основные показатели:**")
            st.write(f"• Минимум: {format_price(price_dist['min'])}")
            st.write(f"• Медиана: {format_price(price_dist['median'])}")
            st.write(f"• Среднее: {format_price(price_dist['mean'])}")
            st.write(f"• Максимум: {format_price(price_dist['max'])}")
        
        with col2:
            st.markdown("**Разброс:**")
            st.write(f"• Стандартное отклонение: {format_price(price_dist['std'])}")
            cv = (price_dist['std'] / price_dist['mean']) if price_dist['mean'] > 0 else 0
            st.write(f"• Коэффициент вариации: {cv:.2f}")
        
        # График распределения цен
        st.subheader("Распределение начальных цен")
        
        fig_hist = px.histogram(
            filtered_df,
            x='initial_price',
            nbins=50,
            title="Гистограмма распределения цен",
            labels={'initial_price': 'Начальная цена (₽)', 'count': 'Количество лотов'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Box plot по регионам
        if selected_region == "Все регионы" and len(filtered_df['region_name'].unique()) > 1:
            st.subheader("Сравнение цен по регионам")
            
            fig_box = px.box(
                filtered_df,
                x='region_name',
                y='initial_price',
                title="Распределение цен по регионам",
                labels={'region_name': 'Регион', 'initial_price': 'Начальная цена (₽)'},
                color='region_name'
            )
            st.plotly_chart(fig_box, use_container_width=True)
    
    # Вкладка 2: Конкуренция
    with tab2:
        st.subheader("Анализ конкуренции")
        
        # Топ заказчиков
        st.markdown("### 🏢 Топ-10 заказчиков")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**По количеству закупок:**")
            top_by_count = competition.top_customers(filtered_df, n=10, by='count')
            fig_top_count = px.bar(
                top_by_count.reset_index(),
                x='lots_count',
                y='customer_name',
                orientation='h',
                title="Топ-10 по количеству лотов",
                labels={'lots_count': 'Количество лотов', 'customer_name': ''},
                color='lots_count',
                color_continuous_scale='Blues'
            )
            fig_top_count.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_top_count, use_container_width=True)
        
        with col2:
            st.markdown("**По объёму закупок:**")
            top_by_volume = competition.top_customers(filtered_df, n=10, by='volume')
            fig_top_volume = px.bar(
                top_by_volume.reset_index(),
                x='total_volume',
                y='customer_name',
                orientation='h',
                title="Топ-10 по объёму (₽)",
                labels={'total_volume': 'Объём (₽)', 'customer_name': ''},
                color='total_volume',
                color_continuous_scale='Greens'
            )
            fig_top_volume.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_top_volume, use_container_width=True)
        
        # Концентрация рынка
        st.markdown("### 📊 Концентрация рынка")
        
        hhi = competition.market_concentration(filtered_df)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("Индекс Херфиндаля-Хиршмана (HHI)", f"{hhi['hhi']:.0f}")
            
            if hhi['hhi'] < 1000:
                concentration = "Низкая концентрация"
                color = "green"
            elif hhi['hhi'] < 1800:
                concentration = "Умеренная концентрация"
                color = "orange"
            else:
                concentration = "Высокая концентрация"
                color = "red"
            
            st.markdown(f"**Уровень:** :{color}[{concentration}]")
            st.write(f"Топ-5 заказчиков: {hhi['top5_share']:.1f}% рынка")
            st.write(f"Топ-10 заказчиков: {hhi['top10_share']:.1f}% рынка")
        
        with col2:
            # Pie chart распределения объёма
            top_10_customers = filtered_df.groupby('customer_name')['initial_price'].sum().nlargest(10)
            other_volume = filtered_df['initial_price'].sum() - top_10_customers.sum()
            
            pie_data = pd.concat([
                top_10_customers,
                pd.Series({'Остальные': other_volume})
            ])
            
            fig_pie = px.pie(
                values=pie_data.values,
                names=pie_data.index,
                title="Распределение объёма закупок",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Вкладка 3: Распределения
    with tab3:
        st.subheader("Распределение закупок")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Распределение по законам
            law_dist = filtered_df['law'].value_counts()
            
            fig_law = px.pie(
                values=law_dist.values,
                names=law_dist.index,
                title="Распределение по законам",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_law, use_container_width=True)
        
        with col2:
            # Распределение по статусам
            status_dist = filtered_df['status'].value_counts().head(10)
            
            fig_status = px.bar(
                x=status_dist.values,
                y=status_dist.index,
                orientation='h',
                title="Топ-10 статусов закупок",
                labels={'x': 'Количество', 'y': 'Статус'},
                color=status_dist.values,
                color_continuous_scale='Viridis'
            )
            fig_status.update_layout(showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)
        
        # Распределение по регионам
        if len(filtered_df['region_name'].unique()) > 1:
            st.subheader("Анализ по регионам")
            
            region_stats = competition.analyze_by_region(filtered_df)
            
            fig_regions = go.Figure()
            
            fig_regions.add_trace(go.Bar(
                name='Количество лотов',
                x=region_stats.index,
                y=region_stats['lots_count'],
                yaxis='y',
                offsetgroup=1
            ))
            
            fig_regions.add_trace(go.Bar(
                name='Объём (млн ₽)',
                x=region_stats.index,
                y=region_stats['total_volume'] / 1_000_000,
                yaxis='y2',
                offsetgroup=2
            ))
            
            fig_regions.update_layout(
                title='Сравнение регионов',
                xaxis=dict(title='Регион'),
                yaxis=dict(title='Количество лотов', side='left'),
                yaxis2=dict(title='Объём (млн ₽)', side='right', overlaying='y'),
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig_regions, use_container_width=True)
    
    # Вкладка 4: Таблица данных
    with tab4:
        st.subheader("Данные о закупках")
        
        # Выбор колонок для отображения
        display_columns = [
            'reg_number', 'object_name', 'customer_name', 
            'initial_price', 'region_name', 'law', 'status'
        ]
        
        display_df = filtered_df[display_columns].copy()
        display_df['initial_price'] = display_df['initial_price'].apply(lambda x: f"{x:,.0f}".replace(",", " "))
        
        # Переименование колонок для читаемости
        display_df.columns = [
            'Номер закупки', 'Объект закупки', 'Заказчик',
            'Начальная цена (₽)', 'Регион', 'Закон', 'Статус'
        ]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500
        )
        
        # Кнопка экспорта
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Скачать данные (CSV)",
            data=csv,
            file_name=f"tenderlens_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Футер
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Данных загружено:** {len(df):,}".replace(",", " "))
    st.sidebar.markdown(f"**После фильтров:** {len(filtered_df):,}".replace(",", " "))
    st.sidebar.markdown(f"**Последнее обновление:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")


if __name__ == "__main__":
    main()
