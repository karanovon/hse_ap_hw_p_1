# Temperature Analysis Service

Небольшой сервис для анализа исторических температурных данных и мониторинга текущей погоды.

## Структура проекта
```text
├── app.py                  # Приложение Streamlit
├── data/
│   └── temperature_data.csv # Исторические температурные данные
├── notebooks/
│   └── ИИ_ДЗ_1.ipynb        # Исследовательский ноутбук
├── requirements.txt         # Зависимости проекта
├── utils/
│   ├── analysis.py          # Анализ и визуализация температур
│   ├── async_monitoring.py  # Асинхронный мониторинг погоды
│   └── sync_monitoring.py   # Синхронный мониторинг погоды
```

## Запуск сервиса

### 1. Установка зависимостей
```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Запуск приложения
```bash
streamlit run app.py
```

**Пример данных** 

В качестве примера входных данных можно использовать файл
`data/temperature_data.csv`, содержащий исторические температурные наблюдения.

**Ссылка на приложение:** https://hseaphwp1-nvgbxqvcmwwemmljkhcir9.streamlit.app/