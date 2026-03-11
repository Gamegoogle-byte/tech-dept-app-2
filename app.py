import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

# Налаштування сторінки
st.set_page_config(page_title="Техвідділ: Планування", layout="wide")
st.title("🏗 Система керування технічним відділом")

# Функція для ініціалізації бази даних
def init_db():
    conn = sqlite3.connect('construction.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  task_name TEXT, 
                  quantity REAL, 
                  price_1_2 REAL, 
                  price_1_3 REAL, 
                  team TEXT, 
                  start_date TEXT, 
                  end_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 1. Завантаження файлу (Тепер приймає .xlsx)
uploaded_file = st.sidebar.file_uploader("Завантажте кошторис (Excel)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Використовуємо read_excel замість read_csv
        # header=3 означає, що ми пропускаємо перші 3 рядки шапки (налаштуйте під свій файл, якщо треба)
        df = pd.read_excel(uploaded_file, header=3)
        
        # Очищення даних (беремо потрібні колонки)
        # Увага: назви колонок мають ТОЧНО збігатися з тими, що у вашому Excel
        cols_to_keep = ['Найменування ', 'кількість', '1.2', '1.3']
        
        # Перевіряємо, чи є такі колонки у файлі
        available_cols = [col for col in cols_to_keep if col in df.columns]
        df = df[available_cols].dropna(subset=[available_cols[0]]) # Видаляємо порожні рядки
        
        st.success("Файл успішно завантажено та розпізнано!")
        
        st.subheader("Крок 1: Виберіть діапазон робіт для планування")
        
        # Вибір діапазону
        start_idx = st.number_input("Початковий рядок", min_value=0, max_value=len(df)-1, value=0)
        end_idx = st.number_input("Кінцевий рядок", min_value=start_idx, max_value=len(df)-1, value=min(10, len(df)-1))
        
        selected_range = df.iloc[start_idx:end_idx+1]
        st.dataframe(selected_range) # Виводимо таблицю на екран
        
        # 2. Розрахунок термінів
        st.subheader("Крок 2: Планування графіка")
        col1, col2 = st.columns(2)
        
        with col1:
            team_size = st.number_input("Кількість людей у бригаді", min_value=1, value=4)
            start_date = st.date_input("Дата початку робіт", datetime.today())
        
        with col2:
            team = st.selectbox("Призначити бригаду", ["Бригада 1", "Бригада 2", "Бригада 3"])
            # Умовний розрахунок людино-днів (потім замінимо на вашу формулу з Excel)
            estimated_man_days = len(selected_range) * 2.5 
            days_needed = estimated_man_days / team_size
            end_date = start_date + timedelta(days=days_needed)
            
            st.info(f"⏱ Орієнтовна дата закінчення: **{end_date.strftime('%d.%m.%Y')}**")
        
        # 3. Збереження в базу
        if st.button("💾 Сформувати завдання та зберегти"):
            conn = sqlite3.connect('construction.db')
            c = conn.cursor()
            
            for index, row in selected_range.iterrows():
                c.execute('''INSERT INTO tasks (task_name, quantity, price_1_2, price_1_3, team, start_date, end_date)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (str(row.get('Найменування ', 'Невідомо')), 
                           float(row.get('кількість', 0)), 
                           float(row.get('1.2', 0)), 
                           float(row.get('1.3', 0)), 
                           team, 
                           start_date.strftime('%Y-%m-%d'), 
                           end_date.strftime('%Y-%m-%d')))
            conn.commit()
            conn.close()
            st.success(f"✅ Успішно! {len(selected_range)} завдань призначено для {team}.")
            
    except Exception as e:
        st.error(f"Помилка при читанні файлу. Перевірте структуру Excel. Деталі: {e}")
else:
    st.info("👈 Будь ласка, завантажте Excel файл у панелі зліва, щоб розпочати.")
