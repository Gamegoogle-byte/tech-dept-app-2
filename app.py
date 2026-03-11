import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="ERP Будівництво", layout="wide")

# --- ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ ---
def init_db():
    conn = sqlite3.connect('construction.db')
    c = conn.cursor()
    # Таблиця завдань (План)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  task_name TEXT, 
                  unit TEXT,
                  quantity_plan REAL, 
                  price REAL, 
                  team TEXT, 
                  start_date TEXT, 
                  end_date TEXT)''')
    # Таблиця виконання (Факт)
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task_id INTEGER,
                  date_reported TEXT,
                  quantity_fact REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- БІЧНЕ МЕНЮ (НАВІГАЦІЯ) ---
st.sidebar.title("Меню навігації")
page = st.sidebar.radio("Оберіть розділ:", 
    ["📥 1. Завантаження та Планування", 
     "👷 2. Кабінет Виконроба (Факт)", 
     "📊 3. Графік робіт (Гант)", 
     "💰 4. Зарплата та Звіти"]
)

# ==========================================
# СТОРІНКА 1: ЗАВАНТАЖЕННЯ ТА ПЛАНУВАННЯ
# ==========================================
if page == "📥 1. Завантаження та Планування":
    st.title("Крок 1: Завантаження кошторису та планування")
    
    uploaded_file = st.file_uploader("Завантажте кошторис у форматі Excel (.xlsx)", type=["xlsx", "xls"])
    
    if uploaded_file:
        # Дозволяємо користувачу вибрати, з якого рядка починається шапка таблиці
        header_row = st.number_input("З якого рядка починається таблиця (шапка)?", min_value=0, value=3)
        
        try:
            df = pd.read_excel(uploaded_file, header=header_row)
            st.success("Файл завантажено! Тепер вкажіть, де знаходяться потрібні дані:")
            
            # Динамічний вибір колонок (щоб не залежати від точних назв у файлі)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                col_name = st.selectbox("Колонка з назвою робіт", df.columns)
            with col2:
                col_unit = st.selectbox("Колонка з одиницями виміру", df.columns)
            with col3:
                col_qty = st.selectbox("Колонка з кількістю", df.columns)
            with col4:
                col_price = st.selectbox("Колонка з ціною для бригади (напр. 1.2 або 1.3)", df.columns)
            
            # Фільтруємо таблицю від порожніх рядків
            df_clean = df.dropna(subset=[col_name]).copy()
            
            st.write("Попередній перегляд даних:")
            st.dataframe(df_clean[[col_name, col_unit, col_qty, col_price]].head())
            
            st.divider()
            st.subheader("Формування завдань для бригад")
            
            # Вибір діапазону робіт
            start_idx = st.number_input("З якого рядка беремо роботи?", min_value=0, max_value=len(df_clean)-1, value=0)
            end_idx = st.number_input("По який рядок?", min_value=start_idx, max_value=len(df_clean)-1, value=min(5, len(df_clean)-1))
            
            selected_tasks = df_clean.iloc[start_idx:end_idx+1]
            st.write("Обрані роботи для передачі в роботу:")
            st.dataframe(selected_tasks[[col_name, col_qty]])
            
            # Планування
            c1, c2, c3 = st.columns(3)
            with c1:
                team = st.selectbox("Призначити бригаду", ["Бригада 1", "Бригада 2", "Бригада 3"])
            with c2:
                start_date = st.date_input("Дата початку", datetime.today())
            with c3:
                end_date = st.date_input("Орієнтовна дата завершення", datetime.today() + timedelta(days=7))
                
            if st.button("💾 Зберегти графік та передати бригаді"):
                conn = sqlite3.connect('construction.db')
                c = conn.cursor()
                for index, row in selected_tasks.iterrows():
                    c.execute('''INSERT INTO tasks (task_name, unit, quantity_plan, price, team, start_date, end_date)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (str(row[col_name]), str(row[col_unit]), float(row[col_qty]), float(row[col_price]), 
                               team, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                conn.commit()
                conn.close()
                st.success(f"✅ {len(selected_tasks)} завдань успішно передано для {team}!")
                
        except Exception as e:
            st.error(f"Помилка зчитування: {e}")

# ==========================================
# СТОРІНКА 2: КАБІНЕТ ВИКОНРОБА (ФАКТ)
# ==========================================
elif page == "👷 2. Кабінет Виконроба (Факт)":
    st.title("Внесення фактично виконаних робіт")
    
    conn = sqlite3.connect('construction.db')
    tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
    
    if not tasks_df.empty:
        # Виконроб обирає свою бригаду
        selected_team = st.selectbox("Оберіть вашу бригаду:", tasks_df['team'].unique())
        
        # Фільтруємо завдання для цієї бригади
        team_tasks = tasks_df[tasks_df['team'] == selected_team]
        
        st.write("Ваші поточні завдання:")
        task_to_report = st.selectbox("Оберіть роботу, яку ви виконали:", team_tasks['task_name'])
        
        # Отримуємо ID обраного завдання та його план
        task_info = team_tasks[team_tasks['task_name'] == task_to_report].iloc[0]
        task_id = task_info['id']
        plan_qty = task_info['quantity_plan']
        unit = task_info['unit']
        
        # Рахуємо, скільки вже було виконано раніше
        progress_df = pd.read_sql_query(f"SELECT SUM(quantity_fact) as total_fact FROM progress WHERE task_id={task_id}", conn)
        total_done = progress_df['total_fact'].iloc[0]
        if pd.isna(total_done): total_done = 0
            
        st.info(f"**За планом:** {plan_qty} {unit} | **Вже виконано:** {total_done} {unit} | **Залишилось:** {plan_qty - total_done} {unit}")
        
        # Внесення факту
        with st.form("fact_form"):
            report_date = st.date_input("Дата виконання", datetime.today())
            new_fact = st.number_input(f"Скільки {unit} виконано за цей період?", min_value=0.0, step=0.1)
            submitted = st.form_submit_button("Відправити звіт")
            
            if submitted:
                c = conn.cursor()
                c.execute("INSERT INTO progress (task_id, date_reported, quantity_fact) VALUES (?, ?, ?)", 
                          (int(task_id), report_date.strftime('%Y-%m-%d'), float(new_fact)))
                conn.commit()
                st.success("✅ Дані успішно збережено!")
                st.rerun()
    else:
        st.warning("Немає активних завдань. Спочатку сплануйте роботи на Кроці 1.")
    conn.close()

# ==========================================
# СТОРІНКА 3: ГРАФІК РОБІТ (ГАНТ)
# ==========================================
elif page == "📊 3. Графік робіт (Гант)":
    st.title("Графік виконання робіт (План / Факт)")
    
    conn = sqlite3.connect('construction.db')
    tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
    progress_df = pd.read_sql_query("SELECT task_id, SUM(quantity_fact) as fact FROM progress GROUP BY task_id", conn)
    conn.close()
    
    if not tasks_df.empty:
        # Об'єднуємо план і факт
        merged_df = pd.merge(tasks_df, progress_df, left_on='id', right_on='task_id', how='left')
        merged_df['fact'] = merged_df['fact'].fillna(0)
        merged_df['progress_percent'] = (merged_df['fact'] / merged_df['quantity_plan']) * 100
        merged_df['progress_percent'] = merged_df['progress_percent'].apply(lambda x: min(x, 100)) # не більше 100%
        
        # Побудова графіка Ганта
        
        fig = px.timeline(merged_df, x_start="start_date", x_end="end_date", y="task_name", color="team", 
                          title="Плановий графік з розподілом по бригадах",
                          hover_data=["quantity_plan", "fact", "progress_percent"])
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Таблиця прогресу (Відставання/Випередження)")
        display_df = merged_df[['task_name', 'team', 'quantity_plan', 'fact', 'unit']].copy()
        display_df['% Виконання'] = merged_df['progress_percent'].round(1).astype(str) + '%'
        display_df.columns = ['Робота', 'Бригада', 'План', 'Факт', 'Од.вим', '% Виконання']
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("Немає даних для графіка.")

# ==========================================
# СТОРІНКА 4: ЗАРПЛАТА ТА ЗВІТИ
# ==========================================
elif page == "💰 4. Зарплата та Звіти":
    st.title("Нарахування ЗП бригадам (на основі факту)")
    
    conn = sqlite3.connect('construction.db')
    # SQL запит, який з'єднує завдання та їх виконання для підрахунку грошей
    query = '''
        SELECT 
            t.team as Бригада,
            t.task_name as Робота,
            p.date_reported as Дата,
            p.quantity_fact as Виконано,
            t.price as Ціна_за_од,
            (p.quantity_fact * t.price) as Сума_до_виплати
        FROM progress p
        JOIN tasks t ON p.task_id = t.id
    '''
    salary_df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not salary_df.empty:
        st.write("Деталізована відомість по всім роботам:")
        st.dataframe(salary_df)
        
        st.subheader("Загальна сума до виплати по бригадах:")
        # Групуємо суми по бригадах
        summary_df = salary_df.groupby('Бригада')['Сума_до_виплати'].sum().reset_index()
        summary_df.columns = ['Бригада', 'Всього нараховано (грн)']
        
        # Виводимо великими цифрами
        cols = st.columns(len(summary_df))
        for idx, row in summary_df.iterrows():
            with cols[idx]:
                st.metric(label=row['Бригада'], value=f"{row['Всього нараховано (грн)']:.2f} ₴")
    else:
        st.info("Ще немає даних про фактичне виконання робіт для розрахунку ЗП.")
