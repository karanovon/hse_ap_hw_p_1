import streamlit as st
import pickle
import pandas as pd
import matplotlib.pyplot as plt

model_features = [
    'name',
    'year',
    'km_driven',
    'fuel',
    'seller_type',
    'transmission',
    'owner',
    'mileage',
    'engine',
    'max_power',
    'seats'
]


def main():

    st.title('HW1 - интерактивное приложение')

    model = load_model()

    eda()

    weights(model)

    upload_data_and_predict(model)


@st.cache_resource
def load_model():
    with open('models/model_pipline.pkl', 'rb') as f:
        model = pickle.load(f)
    return model


def eda():
    st.header('1. EDA')

    st.subheader("Попарные распределения числовых признаков")
    st.image('pictures/pairplot.png')

    st.subheader("Boxplot числовых признаков")
    st.image('pictures/boxplot.png')

    st.subheader("Среднее значение целевой по бакетам числовых переменных")
    st.image('pictures/bin_means.png')

    st.subheader("Матрица корреляций числовых переменных")
    st.image('pictures/correlation_matrix.png')


def weights(model):
    st.header("2. Веса модели")

    ridge_model = model.named_steps['regressor']
    coef = ridge_model.coef_

    preprocessor = model.named_steps['preprocessor']
    feature_names = preprocessor.get_feature_names_out()

    coef_df = pd.DataFrame({'feature': feature_names, 'coef': coef})
    coef_df = coef_df.sort_values('coef', ascending=True)
    coef_df.reset_index(drop=True, inplace=True)

    st.subheader("График важности признаков")
    fig, ax = plt.subplots(figsize=(7, 10))
    ax.barh(coef_df['feature'], coef_df['coef'])
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def upload_data_and_predict(model):
    st.header("3. Загрузка данных для прогноза")

    uploaded_file = st.file_uploader("Выберите CSV файл", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, index_col=0)
            df['prediction'] = model.predict(df[model_features])

            st.dataframe(df.head())
            st.session_state['data'] = df
            st.session_state['features'] = df.columns.tolist()

        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")


if __name__ == "__main__":
    main()
