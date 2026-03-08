"""
Streamlit UI для предсказания цены аренды недвижимости.

Два режима: ввод параметров вручную и оценка по ссылке на объявление Циан.
"""
import os
import re
import logging
import streamlit as st

logger = logging.getLogger(__name__)
import requests
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional, List, Tuple

# Конфигурация: в Docker задать API_BASE_URL=http://backend:8000/api
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Обязательные признаки для режима «по ссылке» (названия для сообщения пользователю)
REQUIRED_FIELDS = [
    ("total_area", "общая площадь"),
    ("rooms_count", "количество комнат"),
    ("floor_number", "этаж"),
    ("floors_count", "этажей в доме"),
    ("build_year", "год постройки"),
    ("repair_type", "тип ремонта"),
    ("material_type", "тип дома"),
]
# Координаты или (район + время до метро)
REQUIRED_GEO = ["coordinates", "district", "travel_time"]

# Русские подписи для выпадающих списков
REPAIR_OPTIONS = [
    ("Евро", "euro"),
    ("Дизайнерский", "design"),
    ("Косметический", "cosmetic"),
    ("Без ремонта", "no"),
]
MATERIAL_OPTIONS = [
    ("Монолит", "monolith"),
    ("Кирпичный", "brick"),
    ("Панельный", "panel"),
    ("Блочный", "block"),
    ("Другой", "none"),
]
# Комнаты: отдельно студия (flat_type=studio, rooms_count=1), затем 1–9 комнат (flat_type=rooms)
ROOM_OPTIONS = [("Студия", 1, "studio")] + [(str(i), i, "rooms") for i in range(1, 10)]
REPAIR_LABELS = {v: k for k, v in REPAIR_OPTIONS}
MATERIAL_LABELS = {v: k for k, v in MATERIAL_OPTIONS}

# Центр Москвы (запасной вариант при ошибке геокодинга)
CENTER_MOSCOW = (55.7558, 37.6173)

st.set_page_config(
    page_title="RentSense - Предсказание цены аренды",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 RentSense - Предсказание цены аренды")
st.caption("По Москве.")
st.markdown("Оценка рыночной стоимости аренды: введите параметры или ссылку на объявление Циан.")


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


def call_search_api(filters: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Вызов API /search. Не передаём пустые строки.
    Возвращает (response_json или None, сообщение об ошибке или None).
    """
    params = {k: v for k, v in filters.items() if v is not None and v != ""}
    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None, "Похожие объявления недоступны"
        return None, str(e)
    except Exception as e:
        return None, "Похожие объявления недоступны"


def fetch_metro_list() -> List[str]:
    """Загрузка списка станций метро из API."""
    try:
        response = requests.get(f"{API_BASE_URL}/metro", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def _geocode_nominatim(address: str) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
    """Nominatim (OSM). Возвращает (координаты или None, сообщение об ошибке)."""
    try:
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter
        geolocator = Nominatim(
            user_agent="RentSense/1.0 (rentsense-app; Moscow rent price prediction)",
            timeout=10,
        )
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)
        for query in (f"{address.strip()}, Москва, Россия", f"Москва, {address.strip()}"):
            location = geocode(query)
            if location:
                return ((location.latitude, location.longitude), None)
    except Exception as e:
        logger.warning("Nominatim geocode failed: %s", e)
        return None, str(e)
    return None, "Адрес не найден (Nominatim)"


def _geocode_yandex(address: str, api_key: str) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
    """Яндекс.Геокодер. Возвращает (координаты или None, сообщение об ошибке)."""
    if not api_key or not api_key.strip():
        return None, "Не задан YANDEX_GEOCODER_API_KEY"
    try:
        from geopy.geocoders import Yandex
        geolocator = Yandex(api_key=api_key.strip(), timeout=10)
        location = geolocator.geocode(f"{address.strip()}, Москва")
        if location:
            return ((location.latitude, location.longitude), None)
    except Exception as e:
        logger.warning("Yandex geocode failed: %s", e)
        return None, str(e)
    return None, "Адрес не найден (Яндекс)"


def geocode_address(address: str) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
    """Геокодинг: при заданном YANDEX_GEOCODER_API_KEY — сначала Яндекс, иначе Nominatim.
    Возвращает (координаты или None, сообщение об ошибке при неудаче)."""
    if not address or not address.strip():
        return None, "Пустой адрес"
    api_key = os.getenv("YANDEX_GEOCODER_API_KEY", "").strip()
    last_error: Optional[str] = None
    if api_key:
        result, err = _geocode_yandex(address, api_key)
        if result is not None:
            return result, None
        last_error = err
    result, err = _geocode_nominatim(address)
    if result is not None:
        return result, None
    if last_error and err:
        return None, f"Яндекс: {last_error}. Fallback Nominatim: {err}"
    return None, last_error or err or "Не удалось определить координаты"


def create_map(lat: float, lng: float, similar_offers: list = None):
    """Создание карты с местоположением и похожими объявлениями."""
    m = folium.Map(location=[lat, lng], zoom_start=13)
    folium.Marker(
        [lat, lng],
        popup="Ваша квартира",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)
    if similar_offers:
        for offer in similar_offers[:10]:
            if offer.get('coordinates') and isinstance(offer['coordinates'], dict):
                c = offer['coordinates']
                if 'lat' in c and 'lng' in c:
                    folium.Marker(
                        [c['lat'], c['lng']],
                        popup=f"Цена: {offer.get('price', 0):,.0f} руб",
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(m)
    return m


def getparams_to_predict_data(resp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразование ответа getparams в данные для POST /predict.
    Поддержка: плоский dict (preparams) или вложенный Params (offers, addresses, ...).
    """
    if "offers" in resp and isinstance(resp["offers"], dict):
        flat = {}
        for table in ("offers", "addresses", "realty_inside", "realty_outside", "realty_details", "offers_details", "developers"):
            if table in resp and isinstance(resp[table], dict):
                flat.update(resp[table])
        flat.setdefault("cian_id", 0)
        data = flat
    else:
        data = dict(resp)
    if "coordinates" in data and data["coordinates"] is not None and not isinstance(data["coordinates"], dict):
        data["coordinates"] = None
    return data


def validate_for_predict(data: Dict[str, Any]) -> List[str]:
    """
    Проверка наличия обязательных признаков для прогноза.
    Возвращает список названий недостающих полей (на русском).
    """
    missing = []
    for key, label in REQUIRED_FIELDS:
        val = data.get(key)
        if val is None:
            missing.append(label)
            continue
        if key in ("total_area", "rooms_count", "floor_number", "floors_count"):
            if isinstance(val, (int, float)) and (val == 0 or (key == "total_area" and val < 5)):
                missing.append(label)
        if key == "build_year":
            try:
                y = int(val)
                if y < 1800 or y > 2030:
                    missing.append(label)
            except (TypeError, ValueError):
                missing.append(label)
    has_coords = data.get("coordinates") and isinstance(data.get("coordinates"), dict) and data["coordinates"].get("lat") is not None and data["coordinates"].get("lng") is not None
    has_district = data.get("district") and str(data.get("district")).strip()
    has_travel = data.get("travel_time") is not None
    if not has_coords and not (has_district and has_travel):
        missing.append("координаты или район и время до метро")
    return missing


def _format_param(value: Any, key: str) -> str:
    """Форматирование значения параметра для отображения."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "—"
    if key == "repair_type":
        return REPAIR_LABELS.get(value, str(value))
    if key == "material_type":
        return MATERIAL_LABELS.get(value, str(value))
    if key == "flat_type":
        return "Студия" if value == "studio" else str(value)
    if isinstance(value, float) and key == "total_area":
        return f"{value:.1f} м²"
    return str(value)


def _approx_bounds(price: float, margin: float = 0.15) -> Tuple[float, float]:
    """Приближённые границы при отсутствии квантильных моделей."""
    return (max(0, price * (1 - margin)), price * (1 + margin))


def render_result(result: Dict[str, Any], data: Dict[str, Any]):
    """Общий блок отображения результата предсказания: метрики, графики, параметры, карта."""
    price = result.get("price", 0) or 0
    p10 = result.get("price_p10")
    p90 = result.get("price_p90")
    total_area = data.get("total_area")
    price_per_sqm = (price / total_area) if total_area and total_area > 0 else None

    # Если квантильные модели не загружены — показываем приближённый диапазон
    use_approx = p10 is None or p90 is None
    if use_approx:
        p10, p90 = _approx_bounds(price)

    # Метрики в одну строку
    cols = st.columns(4)
    with cols[0]:
        st.metric("Предсказанная цена (P50)", f"{price:,.0f} руб".replace(",", " "))
    with cols[1]:
        st.metric("Нижняя граница (P10)", f"{p10:,.0f} руб".replace(",", " "))
    with cols[2]:
        st.metric("Верхняя граница (P90)", f"{p90:,.0f} руб".replace(",", " "))
    with cols[3]:
        st.metric("Цена за м²", f"{price_per_sqm:,.0f} руб/м²".replace(",", " ") if price_per_sqm else "—")

    if use_approx:
        st.caption("P10/P90 рассчитаны приближённо (±15%). Точная вилка доступна при загрузке квантильных моделей на сервере.")

    # График вилки цен
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["P10", "P50", "P90"],
        y=[p10, price, p90],
        marker_color=["#90CAF9", "#1976D2", "#90CAF9"],
        text=[f"{p10:,.0f}".replace(",", " "), f"{price:,.0f}".replace(",", " "), f"{p90:,.0f}".replace(",", " ")],
        textposition="outside",
    ))
    fig.update_layout(
        title="Вилка цен (квантили P10 — медиана P50 — P90)" + (" (приближённо)" if use_approx else ""),
        yaxis_title="Цена (руб)",
        height=320,
        margin=dict(t=50, b=50),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Анализ по похожим объявлениям (как в оценомете: распределение цен, площадь–цена)
    search_filters = {"limit": 100}
    if total_area and total_area > 0:
        search_filters["area_min"] = max(0, total_area - 15)
        search_filters["area_max"] = total_area + 15
    if data.get("rooms_count") is not None:
        search_filters["rooms"] = data.get("rooms_count")
    if data.get("district") and str(data.get("district")).strip():
        search_filters["district"] = data.get("district")
    search_resp, search_err = call_search_api(search_filters)
    offers = search_resp.get("results", []) if search_resp else []

    if offers:
        st.subheader("Анализ по похожим объявлениям")
        df_offers = pd.DataFrame(offers)
        if "price" in df_offers.columns:
            # Распределение цен + вертикальная линия прогноза
            fig_hist = px.histogram(
                df_offers, x="price", nbins=30,
                title="Распределение цен похожих объявлений",
                labels={"price": "Стоимость (руб)", "count": "Количество"},
            )
            fig_hist.add_vline(
                x=price, line_dash="dash", line_color="red",
                annotation_text="Прогноз",
            )
            fig_hist.update_layout(height=320, xaxis_title="Стоимость (руб)", yaxis_title="Количество")
            st.plotly_chart(fig_hist, use_container_width=True)

        if "total_area" in df_offers.columns and "price" in df_offers.columns:
            # Площадь vs цена: точки из БД + наша квартира
            fig_scatter = go.Figure()
            fig_scatter.add_trace(
                go.Scatter(
                    x=df_offers["total_area"], y=df_offers["price"],
                    mode="markers", marker=dict(size=6, color="blue"), name="Похожие объявления",
                )
            )
            if total_area:
                fig_scatter.add_trace(
                    go.Scatter(
                        x=[total_area], y=[price],
                        mode="markers", marker=dict(size=14, color="red", symbol="diamond"),
                        name="Ваш прогноз",
                    )
                )
            fig_scatter.update_layout(
                title="Взаимосвязь площади и стоимости",
                xaxis_title="Общая площадь (м²)", yaxis_title="Стоимость (руб)",
                height=320, showlegend=True,
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        if "rooms_count" in df_offers.columns and "price" in df_offers.columns:
            fig_box = px.box(
                df_offers, x="rooms_count", y="price",
                title="Распределение цен по количеству комнат",
                labels={"rooms_count": "Комнат", "price": "Стоимость (руб)"},
            )
            if total_area and data.get("rooms_count") is not None:
                fig_box.add_trace(
                    go.Scatter(
                        x=[data["rooms_count"]], y=[price],
                        mode="markers", marker=dict(color="red", size=12), name="Ваш прогноз",
                    )
                )
            fig_box.update_layout(height=320)
            st.plotly_chart(fig_box, use_container_width=True)
    else:
        if search_err:
            st.caption("Похожие объявления для графика недоступны: " + search_err)

    # Пояснение про чувствительность к району
    st.info(
        "Если при смене района (например, ЦАО и за МКАД) разница в прогнозе мала — на сервере используется только базовая модель. "
        "Квантильные модели и переобучение с акцентом на локацию дадут более чувствительный к району прогноз."
    )

    # Исходные параметры (сводка)
    st.subheader("Исходные параметры")
    param_keys = [
        ("total_area", "Площадь"),
        ("rooms_count", "Комнат"),
        ("floor_number", "Этаж"),
        ("floors_count", "Этажей в доме"),
        ("build_year", "Год постройки"),
        ("district", "Район"),
        ("metro", "Метро"),
        ("travel_time", "Время до метро (мин)"),
        ("repair_type", "Тип ремонта"),
        ("material_type", "Тип дома"),
    ]
    disp = [_format_param(data.get(k), k) for k, _ in param_keys]
    param_df = pd.DataFrame(
        {"Параметр": [label for _, label in param_keys], "Значение": disp}
    )
    st.dataframe(param_df, use_container_width=True, hide_index=True)

    # Карта
    st.subheader("Карта")
    coords = data.get("coordinates") if isinstance(data.get("coordinates"), dict) else None
    lat = coords.get("lat", CENTER_MOSCOW[0]) if coords else CENTER_MOSCOW[0]
    lng = coords.get("lng", CENTER_MOSCOW[1]) if coords else CENTER_MOSCOW[1]
    m = create_map(lat, lng, None)
    folium_static(m)


# Загрузка списка метро один раз
if "metro_options" not in st.session_state:
    st.session_state["metro_options"] = fetch_metro_list()

metro_options = st.session_state["metro_options"]
metro_choices = [""] + (metro_options if metro_options else [])

mode = st.radio("Режим", ["Ввести параметры", "По ссылке на объявление"], horizontal=True)

if mode == "Ввести параметры":
    with st.sidebar:
        st.header("Параметры квартиры")
        st.markdown("<span style='color:red'>*</span> — обязательные поля", unsafe_allow_html=True)
        address_input = st.text_input("Адрес *", placeholder="ул. Льва Толстого, 5")
        district = st.text_input("Район *", placeholder="Хамовники")
        col1, col2 = st.columns(2)
        with col1:
            floor_number = st.number_input("Этаж *", min_value=1, max_value=100, value=5)
        with col2:
            floors_count = st.number_input("Этажей в доме *", min_value=1, max_value=100, value=10)
        total_area = st.number_input("Общая площадь (м²) *", min_value=10.0, max_value=500.0, value=50.0, step=0.5)
        room_label = st.selectbox("Комнаты *", [r[0] for r in ROOM_OPTIONS], index=1)
        rooms_count, flat_type = next((r[1], r[2]) for r in ROOM_OPTIONS if r[0] == room_label)
        repair_label = st.selectbox("Тип ремонта *", [r[0] for r in REPAIR_OPTIONS], index=0)
        repair_type = next(r[1] for r in REPAIR_OPTIONS if r[0] == repair_label)
        material_label = st.selectbox("Тип дома *", [m[0] for m in MATERIAL_OPTIONS], index=0)
        material_type = next(m[1] for m in MATERIAL_OPTIONS if m[0] == material_label)
        build_year = st.number_input("Год постройки *", min_value=1800, max_value=2025, value=2000)
        metro = st.selectbox("Метро", metro_choices, format_func=lambda x: x if x else "Не выбрано")
        travel_time = st.number_input("Время до метро (мин) *", min_value=0, max_value=60, value=10)

        if st.button("Предсказать цену", type="primary"):
            # Валидация обязательных полей: хотя бы адрес или район; общая площадь > 0
            has_geo = bool(address_input and address_input.strip()) or bool(district and district.strip())
            if not has_geo:
                st.error("Укажите адрес или район (обязательно для расчёта местоположения).")
            elif not total_area or total_area < 10:
                st.error("Общая площадь должна быть не менее 10 м².")
            else:
                address_to_geocode = address_input.strip() if address_input else (f"Москва, {district}".strip() if district else None)
                lat, lng = CENTER_MOSCOW[0], CENTER_MOSCOW[1]
                if address_to_geocode:
                    coords, err_msg = geocode_address(address_to_geocode)
                    if coords:
                        lat, lng = coords
                    else:
                        st.warning("Не удалось определить координаты по адресу. Используется центр Москвы.")
                        if err_msg:
                            st.caption(f"Причина: {err_msg}")

                kitchen_default = (total_area * 0.15) if total_area else 10.0
                living_default = (total_area * 0.6) if total_area else 30.0
                data = {
                    "district": district or None,
                    "street": None,
                    "house": None,
                    "floor_number": int(floor_number),
                    "floors_count": int(floors_count),
                    "total_area": float(total_area),
                    "living_area": float(living_default),
                    "kitchen_area": float(kitchen_default),
                    "rooms_count": int(rooms_count),
                    "flat_type": flat_type,
                    "repair_type": repair_type,
                    "material_type": material_type,
                    "build_year": int(build_year),
                    "metro": metro or None,
                    "travel_time": int(travel_time),
                    "coordinates": {"lat": lat, "lng": lng},
                }
                st.session_state["prediction_data"] = data
                st.session_state["prediction_result"] = call_predict_api(data)

else:
    st.sidebar.header("По ссылке на объявление")
    url_input = st.sidebar.text_input("URL объявления Циан", placeholder="https://www.cian.ru/rent/flat/...")
    if st.sidebar.button("Оценить по ссылке", type="primary") and url_input:
        match = re.search(r"flat/(\d{4,})", url_input)
        if not match:
            st.sidebar.error("Неверный формат ссылки. Вставьте ссылку на объявление аренды квартиры с cian.ru")
        else:
            with st.spinner("Загрузка данных объявления..."):
                try:
                    resp = requests.get(f"{API_BASE_URL}/getparams", params={"url": url_input}, timeout=30)
                    resp.raise_for_status()
                    flat = resp.json()
                except requests.exceptions.HTTPError as e:
                    st.error(f"Не удалось загрузить объявление: {e.response.status_code}. Проверьте ссылку и доступность объявления.")
                    flat = None
                except Exception as e:
                    st.error(f"Ошибка при загрузке: {e}")
                    flat = None
            if flat:
                predict_data = getparams_to_predict_data(flat)
                missing = validate_for_predict(predict_data)
                if missing:
                    st.warning("Для прогноза не хватает: " + ", ".join(missing))
                else:
                    result = call_predict_api(predict_data)
                    if result:
                        st.session_state["prediction_data"] = predict_data
                        st.session_state["prediction_result"] = result

if "prediction_result" in st.session_state and st.session_state["prediction_result"]:
    render_result(st.session_state["prediction_result"], st.session_state.get("prediction_data", {}))
else:
    if mode == "Ввести параметры":
        st.info("Заполните параметры в боковой панели и нажмите «Предсказать цену».")
    else:
        st.info("Вставьте ссылку на объявление Циан и нажмите «Оценить по ссылке».")
