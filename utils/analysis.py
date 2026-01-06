import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def calculate_moving_stats(df, window=30):
    """
    Вычисляет скользящее среднее и стандартное отклонение для каждого города
    """
    result_dfs = []

    for city in df['city'].unique():
        city_df = df[df['city'] == city].copy().sort_values('timestamp')

        city_df['rolling_mean'] = city_df['temperature'].rolling(
            window=window,
            center=True
        ).mean()

        city_df['rolling_std'] = city_df['temperature'].rolling(
            window=window,
            center=True
        ).std()

        result_dfs.append(city_df)

    return pd.concat(result_dfs)


def detect_anomalies(df):
    """
    Определяет аномалии на основе отклонения от скользящего среднего
    """
    df['upper_bound'] = df['rolling_mean'] + 2 * df['rolling_std']
    df['lower_bound'] = df['rolling_mean'] - 2 * df['rolling_std']

    # Определяем аномалии
    df['is_anomaly'] = (
        (df['temperature'] > df['upper_bound']) |
        (df['temperature'] < df['lower_bound'])
    )

    df['anomaly_type'] = np.where(
        df['temperature'] > df['upper_bound'], 'positive',
        np.where(df['temperature'] < df['lower_bound'], 'negative', 'normal')
    )

    return df


def calculate_long_term_trends(df):
    """
    Вычисляет долгосрочные тренды изменения температуры
    """
    trend_data = []

    for city in df['city'].unique():
        city_df = df[df['city'] == city].copy()

        # Годовые средние температуры
        yearly_avg = (
            city_df.groupby('year')['temperature'].mean().reset_index()
        )

        # Линейная регрессия для определения тренда
        x = yearly_avg['year']
        y = yearly_avg['temperature']

        # Коэффициенты линейной регрессии (тренд)
        slope, intercept = np.polyfit(x, y, 1)

        # Темп изменения (градусов в год)
        trend_per_year = slope

        # Классификация тренда
        if trend_per_year > 0.1:
            trend_class = "Сильный рост"
        elif trend_per_year > 0.01:
            trend_class = "Умеренный рост"
        elif trend_per_year < -0.1:
            trend_class = "Сильное снижение"
        elif trend_per_year < -0.01:
            trend_class = "Умеренное снижение"
        else:
            trend_class = "Стабильный"

        trend_data.append({
            'city': city,
            'trend_slope': trend_per_year,
            'trend_class': trend_class,
            'avg_temperature': y.mean(),
            'temperature_range': y.max() - y.min()
        })

    return pd.DataFrame(trend_data)


def plot_city_analysis(city_name, df, trends_df):
    """
    Создает комплексную визуализацию для одного города
    """
    city_data = df[df['city'] == city_name].copy()
    city_trend = trends_df[trends_df['city'] == city_name]

    fig, axes = plt.subplots(3, 2, figsize=(20, 15))
    fig.suptitle(
        f'Анализ температуры: {city_name}',
        fontsize=16,
        fontweight='bold'
    )

    # Исходные данные и скользящее среднее (последний год для наглядности)
    last_year_data = city_data[city_data['year'] == city_data['year'].max()]

    axes[0, 0].plot(last_year_data['timestamp'], last_year_data['temperature'],
                    alpha=0.5, label='Исходные данные')

    axes[0, 0].plot(
        last_year_data['timestamp'], last_year_data['rolling_mean'],
        'r-', linewidth=2, label='Скользящее среднее (30 дней)'
    )

    axes[0, 0].fill_between(
        last_year_data['timestamp'],
        last_year_data['rolling_mean'] - last_year_data['rolling_std'],
        last_year_data['rolling_mean'] + last_year_data['rolling_std'],
        alpha=0.3, color='red', label='±1σ'
    )

    axes[0, 0].set_title(f'Температура {city_name} (последний год)')
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
                       c='red', alpha=0.6, label='Положительные аномалии')
    axes[0, 1].scatter(negative_anomalies['timestamp'],
                       negative_anomalies['temperature'],
                       c='blue', alpha=0.6, label='Отрицательные аномалии')
    axes[0, 1].plot(city_data['timestamp'], city_data['temperature'],
                    alpha=0.2, color='gray')
    axes[0, 1].set_title(f'Выявленные аномалии (всего: {len(anomaly_data)})')
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
    axes[1, 1].plot(yearly_avg['year'], yearly_avg['temperature'],
                    'o-', linewidth=2, markersize=8)

    # Линия тренда
    z = np.polyfit(yearly_avg['year'], yearly_avg['temperature'], 1)
    p = np.poly1d(z)
    axes[1, 1].plot(yearly_avg['year'], p(yearly_avg['year']), "r--",
                    label=f'Тренд: {z[0]:.3f}°C/год')

    axes[1, 1].set_title(
        f'Долгосрочный тренд: {city_trend["trend_class"].values[0]}'
    )
    axes[1, 1].set_xlabel('Год')
    axes[1, 1].set_ylabel('Среднегодовая температура (°C)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    # Сезонные колебания (боксплот)
    seasons_order = ['winter', 'spring', 'summer', 'autumn']
    seasonal_data = [city_data[city_data['season'] == season]['temperature']
                     for season in seasons_order]

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
    Статистика города: {city_name}

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
                    verticalalignment='top', fontfamily='monospace')

    plt.tight_layout()
    plt.show()


def plot_comparative_trends(trends_df):
    """
    Сравнивает тренды температур в разных городах
    Теперь показывает только 2 графика вместо 4
    """

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Тренды по городам (горизонтальные барплоты)
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

    # Добавляем значения на барплоты
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

    # Средние температуры по городам
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

    for i, (bar, value) in enumerate(
        zip(bars_avg, sorted_avg['avg_temperature'])
    ):
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
    plt.show()

    print("СТАТИСТИКА ТРЕНДОВ:")
    print(
        f"• Средний тренд по всем городам: "
        f"{trends_df['trend_slope'].mean():.4f}°C/год"
    )
    print(
        f"• Город с самым сильным потеплением: "
        f"{sorted_trends.iloc[0]['city']} "
        f"({sorted_trends.iloc[0]['trend_slope']:.4f}°C/год)"
    )
    print(
        f"• Город с самым сильным похолоданием: "
        f"{sorted_trends.iloc[-1]['city']} "
        f"({sorted_trends.iloc[-1]['trend_slope']:.4f}°C/год)"
    )
    print(
        f"• Самый жаркий город: "
        f"{sorted_avg.iloc[0]['city']} "
        f"({sorted_avg.iloc[0]['avg_temperature']:.1f}°C)"
    )
    print(
        f"• Самый холодный город: "
        f"{sorted_avg.iloc[-1]['city']} "
        f"({sorted_avg.iloc[-1]['avg_temperature']:.1f}°C)"
    )
