"""
Streamlit UI для предсказания цены аренды недвижимости.

Форма ввода параметров, карта с местоположением, визуализация вилки цен.
"""
import os
import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.graph_objects as go
from typing import Dict, Any, Optional

# Конфигурация: в Docker задать API_BASE_URL=http://backend:8000/api
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="RentSense - Предсказание цены аренды",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 RentSense - Предсказание цены аренды")
st.markdown("Введите параметры квартиры для получения предсказания цены аренды")


def call_predict_api(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Вызов API /predict."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={"data": data, "sysmodel": "catboost"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка при вызове API: {e}")
        return None


def call_search_api(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Вызов API /search."""
    try:
        params = {k: v for k, v in filters.items() if v is not None}
        response = requests.get(
            f"{API_BASE_URL}/search",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка при поиске: {e}")
        return None


def create_map(lat: float, lng: float, similar_offers: list = None):
    """Создание карты с местоположением и похожими объявлениями."""
    m = folium.Map(location=[lat, lng], zoom_start=13)
    
    # Маркер для текущей квартиры
    folium.Marker(
        [lat, lng],
        popup="Ваша квартира",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)
    
    # Маркеры для похожих объявлений
    if similar_offers:
        for offer in similar_offers[:10]:  # Максимум 10 маркеров
            if offer.get('coordinates'):
                coords = offer['coordinates']
                if isinstance(coords, dict) and 'lat' in coords and 'lng' in coords:
                    folium.Marker(
                        [coords['lat'], coords['lng']],
                        popup=f"Цена: {offer.get('price', 0):,.0f} руб",
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(m)
    
    return m


# Боковая панель с формой
with st.sidebar:
    st.header("Параметры квартиры")
    
    district = st.text_input("Район", "")
    street = st.text_input("Улица", "")
    house = st.text_input("Дом", "")
    
    col1, col2 = st.columns(2)
    with col1:
        floor_number = st.number_input("Этаж", min_value=1, max_value=100, value=5)
    with col2:
        floors_count = st.number_input("Этажей в доме", min_value=1, max_value=100, value=10)
    
    total_area = st.number_input("Общая площадь (м²)", min_value=10.0, max_value=500.0, value=50.0, step=0.5)
    
    col1, col2 = st.columns(2)
    with col1:
        living_area = st.number_input("Жилая площадь (м²)", min_value=1.0, max_value=500.0, value=30.0, step=0.5)
    with col2:
        kitchen_area = st.number_input("Площадь кухни (м²)", min_value=1.0, max_value=100.0, value=10.0, step=0.5)
    
    rooms_count = st.selectbox("Количество комнат", [1, 2, 3, 4, 5, 6, 7, 8, 9], index=1)
    
    repair_type = st.selectbox("Тип ремонта", ["euro", "design", "cosmetic", "no"], index=0)
    
    material_type = st.selectbox("Тип дома", ["monolith", "brick", "panel", "block", "none"], index=0)
    
    build_year = st.number_input("Год постройки", min_value=1800, max_value=2025, value=2000)
    
    metro = st.text_input("Метро", "")
    travel_time = st.number_input("Время до метро (мин)", min_value=0, max_value=60, value=10)
    
    # Координаты (если известны)
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Широта", min_value=55.0, max_value=56.0, value=55.7558, step=0.0001, format="%.4f")
    with col2:
        lng = st.number_input("Долгота", min_value=37.0, max_value=38.0, value=37.6173, step=0.0001, format="%.4f")
    
    if st.button("Предсказать цену", type="primary"):
        # Подготовка данных для API
        data = {
            "district": district,
            "street": street,
            "house": house,
            "floor_number": floor_number,
            "floors_count": floors_count,
            "total_area": total_area,
            "living_area": living_area,
            "kitchen_area": kitchen_area,
            "rooms_count": rooms_count,
            "repair_type": repair_type,
            "material_type": material_type,
            "build_year": build_year,
            "metro": metro,
            "travel_time": travel_time,
            "coordinates": {"lat": lat, "lng": lng}
        }
        
        # Сохранение в session state
        st.session_state['prediction_data'] = data
        st.session_state['prediction_result'] = call_predict_api(data)

# Основная область
if 'prediction_result' in st.session_state and st.session_state['prediction_result']:
    result = st.session_state['prediction_result']
    data = st.session_state.get('prediction_data', {})
    
    # Отображение результата
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Предсказанная цена (P50)", f"{result.get('price', 0):,.0f} руб")
    
    if result.get('price_p10') and result.get('price_p90'):
        with col2:
            st.metric("Нижняя граница (P10)", f"{result.get('price_p10', 0):,.0f} руб")
        with col3:
            st.metric("Верхняя граница (P90)", f"{result.get('price_p90', 0):,.0f} руб")
    
    # Визуализация вилки цен
    if result.get('price_p10') and result.get('price_p90'):
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['P10', 'P50', 'P90'],
            y=[result['price_p10'], result['price'], result['price_p90']],
            marker_color=['lightblue', 'blue', 'lightblue'],
            text=[f"{result['price_p10']:,.0f}", f"{result['price']:,.0f}", f"{result['price_p90']:,.0f}"],
            textposition='outside'
        ))
        
        fig.update_layout(
            title="Вилка цен (P10 - P50 - P90)",
            yaxis_title="Цена (руб)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Карта
    st.subheader("Карта")
    if data.get('coordinates'):
        coords = data['coordinates']
        lat = coords.get('lat', 55.7558)
        lng = coords.get('lng', 37.6173)
        
        # Поиск похожих объявлений
        search_filters = {
            'district': data.get('district'),
            'area_min': data.get('total_area', 0) - 10,
            'area_max': data.get('total_area', 0) + 10,
            'rooms': data.get('rooms_count'),
            'limit': 20
        }
        
        similar_offers = call_search_api(search_filters)
        offers_list = similar_offers.get('results', []) if similar_offers else []
        
        m = create_map(lat, lng, offers_list)
        folium_static(m)
        
        # Таблица похожих объявлений
        if offers_list:
            st.subheader("Похожие объявления")
            df = pd.DataFrame(offers_list)
            st.dataframe(df[['price', 'total_area', 'rooms_count', 'district', 'metro']], use_container_width=True)
    
else:
    st.info("Заполните форму и нажмите 'Предсказать цену'")
