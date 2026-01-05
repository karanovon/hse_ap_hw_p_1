from datetime import datetime

import requests


def get_current_temperature_sync(
        city_name,
        api_key,
        base_url,
        country_code=None
):
    """
    Синхронно получает текущую температуру города через OpenWeatherMap API
    """
    # Формируем параметры запроса
    params = {
        'q': f"{city_name},{country_code}" if country_code else city_name,
        'appid': api_key,
        'units': 'metric'
    }

    try:
        # Выполняем HTTP GET запрос к API
        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            temperature = data['main']['temp']
            description = data['weather'][0]['description']
            return temperature, response.status_code, description
        else:
            return None, response.status_code, None

    except Exception as e:
        print(f"Ошибка при получении температуры для города {city_name}: {e}")
        return None, None, None


def analyze_temperature_anomaly(
    city_name,
    current_temp,
    historical_df
):
    """
    Анализирует является ли текущая температура аномальной
    """
    # Фильтруем исторические данные для выбранного города
    city_data = historical_df[historical_df['city'] == city_name]

    # Получаем текущий месяц для определения сезона
    current_month = datetime.now().month

    # Определяем сезон на основе месяца
    month_to_season = {
        12: 'winter', 1: 'winter', 2: 'winter',
        3: 'spring', 4: 'spring', 5: 'spring',
        6: 'summer', 7: 'summer', 8: 'summer',
        9: 'autumn', 10: 'autumn', 11: 'autumn'
    }
    current_season = month_to_season.get(current_month, 'winter')

    # Фильтруем данные для текущего сезона
    season_data = city_data[city_data['season'] == current_season]

    if len(season_data) == 0:
        return {"error": "Нет исторических данных для анализа"}

    # Вычисляем статистики для текущего сезона
    mean_temp = season_data['temperature'].mean()
    std_temp = season_data['temperature'].std()

    # Определяем границы нормы (среднее ± 2 стандартных отклонения)
    lower_bound = mean_temp - 2 * std_temp
    upper_bound = mean_temp + 2 * std_temp

    # Проверяем, является ли температура аномальной
    is_anomaly = current_temp < lower_bound or current_temp > upper_bound
    anomaly_type = None

    if is_anomaly:
        if current_temp < lower_bound:
            anomaly_type = "negative"
        else:
            anomaly_type = "positive"

    # Определяем зону температуры
    if current_temp < mean_temp - std_temp:
        zone = "Ниже среднего"
    elif current_temp > mean_temp + std_temp:
        zone = "Выше среднего"
    else:
        zone = "В пределах нормы"

    return {
        "city": city_name,
        "current_temperature": current_temp,
        "season": current_season,
        "historical_mean": round(mean_temp, 2),
        "historical_std": round(std_temp, 2),
        "normal_range": (round(lower_bound, 2), round(upper_bound, 2)),
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
        "temperature_zone": zone,
        "deviation_from_mean": round(current_temp - mean_temp, 2)
    }


def test_sync_monitoring(historical_df, test_cities, api_key, base_url):
    """
    Тестирует синхронный мониторинг температуры для нескольких городов
    """

    print("СИНХРОННЫЙ МОНИТОРИНГ ТЕМПЕРАТУРЫ")
    print()

    for city in test_cities:
        print(f"Анализ города: {city}")

        # Получаем текущую температуру
        current_temp, status, description = get_current_temperature_sync(
            city, api_key, base_url
        )

        if current_temp is not None:
            print(f"   Текущая температура: {current_temp:.1f}°C")
            print(f"   Описание погоды: {description}")

            analysis = analyze_temperature_anomaly(
                city, current_temp, historical_df
            )

            print(f"   Сезон: {analysis['season']}")
            print(f"   Историческое среднее: {analysis['historical_mean']}°C")
            print(f"   Нормальный диапазон: {analysis['normal_range'][0]:.1f} - {analysis['normal_range'][1]:.1f}°C")
            print(f"   Отклонение от среднего: {analysis['deviation_from_mean']:+.1f}°C")

            if analysis['is_anomaly']:
                print(f"   ⚠️  АНОМАЛИЯ: {analysis['anomaly_type']}")
            else:
                print("   ✅ Температура в пределах нормы")
        else:
            print(f"   Не удалось получить данные для города {city}")
            print(f"   Код ошибки: {status}")
