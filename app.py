import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Техвідділ: Планування", layout="wide")

st.title("🏗 Система керування технічним відділом")

# 1. Завантаження файлу
uploaded_file = st.sidebar.file_uploader("Завантажте кошторис (CSV)", type="csv")

if uploaded_file:
    # Завантаження та обробка даних
    df = pd.read_csv(uploaded_file, header=3)
    # Залишаємо лише важливі колонки
    df = df[['Найменування ', 'кількість', '1.2', '1.3']].dropna(subset=['Найменування '])
    
    st.subheader("Виберіть діапазон робіт для планування")
    
    # Вибір діапазону (індексів)
    start_idx = st.number_input("Початковий рядок", min_value=0, max_value=len(df)-1)
    end_idx = st.number_input("Кінцевий рядок", min_value=start_idx, max_value=len(df)-1)
    
    selected_range = df.iloc[start_idx:end_idx+1]
    st.write("Вибрані роботи:", selected_range)
    
    # 2. Розрахунок термінів
    st.subheader("Планування графіка")
    team_size = st.number_input("Кількість людей у бригаді", min_value=1, value=5)
    start_date = st.date_input("Дата початку робіт", datetime.today())
    
    # Припускаємо, що у вас є фіксована норма продуктивності
    # Логіка: припустимо, 1 людино-день = 8 годин роботи (або одиниця згідно вашої бази)
    total_man_days = 200 # Тут можна додати логіку підрахунку з вашого файлу
    
    days_needed = total_man_days / team_size
    end_date = start_date + timedelta(days=days_needed)
    
    st.info(f"Орієнтовна дата закінчення: {end_date.strftime('%d.%m.%Y')}")
    
    # 3. Призначення бригади
    team = st.selectbox("Призначити бригаду", ["Бригада 1", "Бригада 2", "Бригада 3"])
    
    if st.button("Сформувати завдання"):
        st.success(f"Завдання для {team} сформовано та записано в базу.")
        # Тут буде код для запису в SQLite
