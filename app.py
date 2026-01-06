import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from utils.analysis import (
    calculate_long_term_trends,
    calculate_moving_stats,
    detect_anomalies,
)
from utils.sync_monitoring import (
    analyze_temperature_anomaly,
    get_current_temperature_sync,
)

# Настройка страницы
st.set_page_config(
    page_title="Анализ температурных данных",
    layout="wide"
)

# Заголовок приложения
st.title("Анализ температурных данных")
st.markdown("""
    Это приложение позволяет анализировать исторические температурные данные
    и сравнивать их с текущей погодой через OpenWeatherMap API.
""")

# Вкладки
tab1, tab2, tab3 = st.tabs([
    "Анализ города",
    "Сравнение городов",
    "Текущая погода"
])

# Инициализация состояния сессии
if 'df' not in st.session_state:
    st.session_state.df = None
if 'trends_df' not in st.session_state:
    st.session_state.trends_df = None
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""


# Боковая панель для загрузки данных и настроек
with st.sidebar:
    st.header("Настройки")

    # Загрузка файла с данными
    uploaded_file = st.file_uploader(
        "Загрузите файл с температурными данными",
        type=['csv'],
        help="Ожидается CSV файл с колонками: city, timestamp, temperature"
    )

    if uploaded_file is not None:
        try:
            # Загружаем данные
            df = pd.read_csv(uploaded_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['year'] = df['timestamp'].dt.year
            df['month'] = df['timestamp'].dt.month

            # Сопоставление месяцев с сезонами
            month_to_season = {
                12: 'winter', 1: 'winter', 2: 'winter',
                3: 'spring', 4: 'spring', 5: 'spring',
                6: 'summer', 7: 'summer', 8: 'summer',
                9: 'autumn', 10: 'autumn', 11: 'autumn'
            }
            df['season'] = df['month'].map(month_to_season)

            # Вычисляем статистики
            with st.spinner("Обработка данных..."):

                # Скользящие статистики
                df_with_stats = calculate_moving_stats(df, window=30)

                # Обнаружение аномалий
                df_with_anomalies = detect_anomalies(df_with_stats)

                # Долгосрочные тренды
                trends_df = calculate_long_term_trends(df_with_anomalies)

                # Сохраняем в сессию
                st.session_state.df = df
                st.session_state.processed_df = df_with_anomalies
                st.session_state.trends_df = trends_df

            st.success("Данные успешно загружены!")

        except Exception as e:
            st.error(f"Ошибка при загрузке файла: {e}")

    # Форма для API ключа
    st.divider()
    st.subheader("OpenWeatherMap API")
    api_key = st.text_input(
        "Введите API ключ",
        type="password",
        help="Получите ключ на https://openweathermap.org/api",
        value=st.session_state.api_key
    )

    if api_key:
        st.session_state.api_key = api_key
        st.success("API ключ сохранен")
    else:
        st.warning("Введите API ключ для отображения текущей погоды")


# Вкладка 1: Анализ города
with tab1:
    st.header("Детальный анализ города")

    if st.session_state.processed_df is None:
        st.warning("Загрузите данные для начала анализа")
    else:
        # Выбор города
        cities = sorted(st.session_state.processed_df['city'].unique())
        selected_city = st.selectbox(
            "Выберите город для анализа",
            cities,
            index=0 if len(cities) > 0 else None
        )

        if selected_city:
            col1, col2, col3 = st.columns(3)

            with col1:

                city_data = st.session_state.processed_df[
                    st.session_state.processed_df['city'] == selected_city
                ]

                st.metric(
                    "Средняя температура",
                    f"{city_data['temperature'].mean():.1f}°C"
                )

            with col2:
                st.metric(
                    "Максимальная температура",
                    f"{city_data['temperature'].max():.1f}°C"
                )

            with col3:
                st.metric(
                    "Минимальная температура",
                    f"{city_data['temperature'].min():.1f}°C"
                )

            anomalies = city_data[city_data['is_anomaly']]
            positive_anomalies = anomalies[anomalies['anomaly_type'] == 'positive']
            negative_anomalies = anomalies[anomalies['anomaly_type'] == 'negative']

            col4, col5 = st.columns(2)
            with col4:
                st.metric("Всего аномалий", len(anomalies))
            with col5:
                if len(anomalies) > 0:
                    st.metric(
                        "Положительные/отрицательные",
                        f"{len(positive_anomalies)}/{len(negative_anomalies)}"
                    )

            st.subheader("Визуализация анализа")

            fig, axes = plt.subplots(3, 2, figsize=(20, 15))
            fig.suptitle(
                f'Анализ температуры: {selected_city}',
                fontsize=16,
                fontweight='bold'
            )

            # Исходные данные и скользящее среднее
            city_data = st.session_state.processed_df[
                st.session_state.processed_df['city'] == selected_city
            ].copy()
            last_year = city_data['year'].max()
            last_year_data = city_data[city_data['year'] == last_year]

            axes[0, 0].plot(last_year_data['timestamp'],
                            last_year_data['temperature'],
                            alpha=0.5, label='Исходные данные')
            axes[0, 0].plot(
                last_year_data['timestamp'],
                last_year_data['rolling_mean'],
                'r-', linewidth=2,
                label='Скользящее среднее (30 дней)'
            )
            axes[0, 0].fill_between(
                last_year_data['timestamp'],
                last_year_data['rolling_mean'] - last_year_data['rolling_std'],
                last_year_data['rolling_mean'] + last_year_data['rolling_std'],
                alpha=0.3, color='red', label='±1σ'
            )
            axes[0, 0].set_title(f'Температура {selected_city} ({last_year} год)')
            axes[0, 0].set_xlabel('Дата')
            axes[0, 0].set_ylabel('Температура (°C)')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

            # Аномалии
            anomaly_data = city_data[city_data['is_anomaly']]
            positive_anomalies = anomaly_data[
                anomaly_data['anomaly_type'] == 'positive'
            ]
            negative_anomalies = anomaly_data[
                anomaly_data['anomaly_type'] == 'negative'
            ]

            axes[0, 1].scatter(positive_anomalies['timestamp'],
                                positive_anomalies['temperature'],
                                c='red', alpha=0.6,
                                label='Положительные аномалии')
            axes[0, 1].scatter(negative_anomalies['timestamp'],
                                negative_anomalies['temperature'],
                                c='blue', alpha=0.6,
                                label='Отрицательные аномалии')
            axes[0, 1].plot(city_data['timestamp'],
                            city_data['temperature'],
                            alpha=0.2, color='gray')
            axes[0, 1].set_title(
                f'Выявленные аномалии (всего: {len(anomaly_data)})'
            )
            axes[0, 1].set_xlabel('Дата')
            axes[0, 1].set_ylabel('Температура (°C)')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)

            # Распределение аномалий по сезонам
            if len(anomaly_data) > 0:
                season_anomalies = anomaly_data.groupby('season')['is_anomaly'].count()
                axes[1, 0].bar(season_anomalies.index,
                                season_anomalies.values,
                                color='orange')
                axes[1, 0].set_title('Распределение аномалий по сезонам')
                axes[1, 0].set_xlabel('Сезон')
                axes[1, 0].set_ylabel('Количество аномалий')

            # Годовые средние температуры и тренд
            yearly_avg = city_data.groupby('year')['temperature'].mean().reset_index()
            axes[1, 1].plot(yearly_avg['year'],
                            yearly_avg['temperature'],
                            'o-', linewidth=2, markersize=8)

            # Линия тренда
            z = np.polyfit(yearly_avg['year'], yearly_avg['temperature'], 1)
            p = np.poly1d(z)
            axes[1, 1].plot(yearly_avg['year'],
                            p(yearly_avg['year']),
                            "r--",
                            label=f'Тренд: {z[0]:.3f}°C/год')

            # Классификация тренда
            city_trend = st.session_state.trends_df[
                st.session_state.trends_df['city'] == selected_city
            ]

            if not city_trend.empty:
                axes[1, 1].set_title(
                    f'Долгосрочный тренд: {city_trend["trend_class"].values[0]}'
                )
            axes[1, 1].set_xlabel('Год')
            axes[1, 1].set_ylabel('Среднегодовая температура (°C)')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)

            # Сезонные колебания
            seasons_order = ['winter', 'spring', 'summer', 'autumn']
            seasonal_data = [
                city_data[city_data['season'] == season]['temperature']
                for season in seasons_order
            ]

            bp = axes[2, 0].boxplot(seasonal_data, patch_artist=True)
            axes[2, 0].set_title('Сезонное распределение температур')
            axes[2, 0].set_xlabel('Сезон')
            axes[2, 0].set_ylabel('Температура (°C)')
            axes[2, 0].set_xticklabels(['winter', 'spring', 'summer', 'autumn'])

            # Цвета для боксплотов
            colors = ['lightblue', 'lightgreen', 'lightcoral', 'gold']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)

            # Сводная информация
            axes[2, 1].axis('off')
            info_text = f"""
            Статистика города: {selected_city}

            Средняя температура: {city_data['temperature'].mean():.2f}°C
            Стандартное отклонение: {city_data['temperature'].std():.2f}°C
            Минимальная температура: {city_data['temperature'].min():.2f}°C
            Максимальная температура: {city_data['temperature'].max():.2f}°C

            Обнаружено аномалий: {len(anomaly_data)}
            - Положительных: {len(positive_anomalies)}
            - Отрицательных: {len(negative_anomalies)}

            Долгосрочный тренд:
            - Изменение температуры: {city_trend['trend_slope'].values[0]:.3f}°C/год
            - Классификация: {city_trend['trend_class'].values[0]}
            """
            axes[2, 1].text(0.1, 0.9, info_text, fontsize=12,
                            verticalalignment='top',
                            fontfamily='monospace')

            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)


# Вкладка 2: Сравнение городов
with tab2:
    st.header("Сравнительный анализ городов")

    if st.session_state.trends_df is None:
        st.warning("Загрузите данные для сравнения городов")
    else:
        st.subheader("Таблица трендов")

        display_df = st.session_state.trends_df.copy()
        display_df['trend_slope'] = display_df['trend_slope'].round(4)
        display_df['avg_temperature'] = display_df['avg_temperature'].round(2)
        display_df['temperature_range'] = display_df['temperature_range'].round(2)

        display_df = display_df.rename(columns={
            'city': 'Город',
            'trend_slope': 'Тренд (°C/год)',
            'trend_class': 'Классификация тренда',
            'avg_temperature': 'Средняя темп. (°C)',
            'temperature_range': 'Диапазон темп. (°C)'
        })

        sort_by = st.selectbox(
            "Сортировать по",
            ['Тренд (°C/год)', 'Средняя темп. (°C)', 'Диапазон темп. (°C)']
        )

        ascending = st.checkbox("По возрастанию", value=False)

        if sort_by == 'Тренд (°C/год)':
            display_df = display_df.sort_values('Тренд (°C/год)',
                                              ascending=ascending)
        elif sort_by == 'Средняя темп. (°C)':
            display_df = display_df.sort_values('Средняя темп. (°C)',
                                              ascending=ascending)
        else:
            display_df = display_df.sort_values('Диапазон темп. (°C)',
                                              ascending=ascending)

        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True
        )

        st.subheader("Визуализация сравнения")

        try:
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

            trends_df = st.session_state.trends_df

            sorted_trends = trends_df.sort_values('trend_slope', ascending=False)
            colors = ['red' if x > 0 else 'blue' for x in sorted_trends['trend_slope']]

            bars = axes[0].barh(sorted_trends['city'],
                               sorted_trends['trend_slope'],
                               color=colors)
            axes[0].set_title('Скорость изменения температуры по городам',
                             fontsize=14,
                             fontweight='bold')
            axes[0].set_xlabel('Изменение температуры (°C/год)', fontsize=12)
            axes[0].axvline(x=0, color='black', linestyle='-', linewidth=0.5)
            axes[0].grid(True, alpha=0.3, axis='x')

            for i, (bar, value) in enumerate(zip(bars, sorted_trends['trend_slope'])):
                if value >= 0:
                    axes[0].text(
                        value + 0.001, bar.get_y() + bar.get_height()/2,
                        f'{value:.3f}', ha='left', va='center', fontsize=9
                    )
                else:
                    axes[0].text(
                        value - 0.001, bar.get_y() + bar.get_height()/2,
                        f'{value:.3f}', ha='right', va='center', fontsize=9
                    )

            sorted_avg = trends_df.sort_values('avg_temperature', ascending=False)
            bars_avg = axes[1].barh(
                sorted_avg['city'],
                sorted_avg['avg_temperature'],
                color=plt.cm.plasma(np.linspace(0.2, 0.8, len(sorted_avg)))
            )
            axes[1].set_title('Средние температуры по городам',
                             fontsize=14,
                             fontweight='bold')
            axes[1].set_xlabel('Средняя температура (°C)', fontsize=12)
            axes[1].grid(True, alpha=0.3, axis='x')

            for i, (bar, value) in enumerate(zip(bars_avg, sorted_avg['avg_temperature'])):
                axes[1].text(
                    value + 0.1, bar.get_y() + bar.get_height()/2,
                    f'{value:.1f}°C', ha='left', va='center', fontsize=9
                )

            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='red', edgecolor='red',
                     label='Положительный тренд (потепление)'),
                Patch(facecolor='blue', edgecolor='blue',
                     label='Отрицательный тренд (похолодание)')
            ]
            axes[0].legend(handles=legend_elements, loc='lower right', fontsize=10)

            plt.suptitle('Сравнительный анализ температурных характеристик городов',
                        fontsize=16, fontweight='bold', y=1.02)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            st.subheader("Статистика трендов")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                avg_trend = trends_df['trend_slope'].mean()
                st.metric(
                    "Средний тренд",
                    f"{avg_trend:.4f}°C/год",
                    delta=f"{avg_trend:.4f}°C/год"
                )

            with col2:
                strongest_warming = sorted_trends.iloc[0]
                st.metric(
                    "Самое сильное потепление",
                    f"{strongest_warming['trend_slope']:.4f}°C/год",
                    delta=f"{strongest_warming['city']}"
                )

            with col3:
                strongest_cooling = sorted_trends.iloc[-1]
                st.metric(
                    "Самое сильное похолодание",
                    f"{strongest_cooling['trend_slope']:.4f}°C/год",
                    delta=f"{strongest_cooling['city']}"
                )

            with col4:
                hottest_city = sorted_avg.iloc[0]
                st.metric(
                    "Самый жаркий город",
                    f"{hottest_city['avg_temperature']:.1f}°C",
                    delta=f"{hottest_city['city']}"
                )

        except Exception as e:
            st.error(f"Ошибка при визуализации сравнения: {e}")

# Вкладка 3: Текущая погода
with tab3:
    st.header("Мониторинг текущей погоды")

    if st.session_state.processed_df is None:
        st.warning("Загрузите данные для анализа текущей погоды")
    elif not st.session_state.api_key:
        st.warning("Введите API ключ OpenWeatherMap в боковой панели")
    else:
        # Выбор города для мониторинга
        cities = sorted(st.session_state.processed_df['city'].unique())
        selected_city = st.selectbox(
            "Выберите город для мониторинга",
            cities,
            key="monitoring_city"
        )

        if selected_city and st.button("Получить текущую температуру"):
            with st.spinner("Получение данных..."):
                try:
                    # Параметры API
                    base_url = "https://api.openweathermap.org/data/2.5/weather"

                    # Получаем текущую температуру
                    current_temp, status, description = get_current_temperature_sync(
                        selected_city,
                        st.session_state.api_key,
                        base_url
                    )

                    if status == 401:
                        st.error("Неверный API ключ. Проверьте ключ и попробуйте снова.")
                        st.info("Получите ключ на https://openweathermap.org/api")
                    elif current_temp is not None:

                        analysis = analyze_temperature_anomaly(
                            selected_city,
                            current_temp,
                            st.session_state.processed_df
                        )

                        if "error" in analysis:
                            st.error(analysis["error"])
                        else:
                            # Отображаем результаты
                            col1, col2 = st.columns(2)

                            with col1:
                                st.subheader(selected_city)

                                st.metric(
                                    f"Текущая температура",
                                    f"{current_temp:.1f}°C",
                                    delta=f"{analysis['deviation_from_mean']:+.1f}°C от среднего"
                                )

                                st.write(f"**Описание:** {description}")
                                st.write(f"**Сезон:** {analysis['season']}")

                                deviation = analysis['deviation_from_mean']
                                if deviation > 0:
                                    st.progress(
                                        min(1.0, deviation / 10),
                                        text=f"Выше среднего на {deviation:.1f}°C"
                                    )
                                else:
                                    st.progress(
                                        max(0.0, 1 + deviation / 10),
                                        text=f"Ниже среднего на {abs(deviation):.1f}°C"
                                    )

                            with col2:
                                st.subheader("Анализ")

                                # Статистика
                                st.write(f"**Историческое среднее:** {analysis['historical_mean']}°C")
                                st.write(f"**Стандартное отклонение:** {analysis['historical_std']}°C")
                                st.write(f"**Нормальный диапазон:** {analysis['normal_range'][0]:.1f}°C - {analysis['normal_range'][1]:.1f}°C")

                                # Статус аномалии
                                if analysis['is_anomaly']:
                                    if analysis['anomaly_type'] == 'positive':
                                        st.error(f"⚠️ **ПОЛОЖИТЕЛЬНАЯ АНОМАЛИЯ**")
                                        st.write(f"Температура значительно выше нормы для сезона {analysis['season']}")
                                    else:
                                        st.error(f"⚠️ **ОТРИЦАТЕЛЬНАЯ АНОМАЛИЯ**")
                                        st.write(f"Температура значительно ниже нормы для сезона {analysis['season']}")
                                else:
                                    st.success(f"✅ **ТЕМПЕРАТУРА В НОРМЕ**")
                                    st.write(f"Температура находится в пределах нормального диапазона для сезона {analysis['season']}")

                                st.write(f"**Зона температуры:** {analysis['temperature_zone']}")

                    else:
                        st.error(f"Не удалось получить данные для города {selected_city}")
                        if status:
                            st.write(f"Код ошибки: {status}")

                except Exception as e:
                    st.error(f"Ошибка при получении данных: {e}")

        st.divider()
        st.subheader("Множественный мониторинг")

        selected_cities = st.multiselect(
            "Выберите города для сравнения",
            cities,
            default=cities[:3] if len(cities) >= 3 else cities
        )

        if selected_cities and st.button("Сравнить города"):
            if not st.session_state.api_key:
                st.error("Введите API ключ для сравнения городов")
            else:
                with st.spinner("Получение данных для выбранных городов..."):
                    try:
                        base_url = "https://api.openweathermap.org/data/2.5/weather"
                        results = []

                        for city in selected_cities:
                            current_temp, status, description = get_current_temperature_sync(
                                city,
                                st.session_state.api_key,
                                base_url
                            )

                            if current_temp is not None:
                                analysis = analyze_temperature_anomaly(
                                    city,
                                    current_temp,
                                    st.session_state.processed_df
                                )

                                if "error" not in analysis:
                                    results.append({
                                        'Город': city,
                                        'Температура': f"{current_temp:.1f}°C",
                                        'Отклонение': f"{analysis['deviation_from_mean']:+.1f}°C",
                                        'Сезон': analysis['season'],
                                        'Статус': 'Аномалия' if analysis['is_anomaly'] else 'Норма',
                                        'Тип аномалии': analysis['anomaly_type'] if analysis['is_anomaly'] else 'Нет'
                                    })

                        if results:
                            results_df = pd.DataFrame(results)

                            st.dataframe(
                                results_df,
                                width='stretch',
                                hide_index=True
                            )

                        else:
                            st.warning("Не удалось получить данные для выбранных городов")

                    except Exception as e:
                        st.error(f"Ошибка при сравнении городов: {e}")

st.divider()
st.markdown("""
---
**Примечаниe:**
1. Для работы с текущей погодой необходим API ключ OpenWeatherMap
2. Исторические данные должны содержать колонки: city, timestamp, temperature
3. Данные обрабатываются с использованием скользящего среднего (30 дней)
4. Аномалии определяются как отклонения за пределы ±2σ от скользящего среднего
""")
