import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'manicure-salon-secret-key-2024'

DATABASE = 'manicure_salon.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT
            )
        ''')

        # Таблица услуг
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                duration INTEGER NOT NULL
            )
        ''')

        # Таблица записей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES users (id),
                FOREIGN KEY (master_id) REFERENCES users (id),
                FOREIGN KEY (service_id) REFERENCES services (id)
            )
        ''')

        # Добавляем услуги только если таблица пустая
        cursor.execute('SELECT COUNT(*) FROM services')
        if cursor.fetchone()[0] == 0:
            services = [
                ('Классический маникюр', 'Обработка ногтей, придание формы, покрытие лаком', 1500, 60),
                ('Аппаратный маникюр', 'Маникюр с использованием аппарата', 2000, 90),
                ('SPA маникюр', 'Маникюр с питательными ванночками и массажем', 2500, 120),
                ('Покрытие гель-лаком', 'Стойкое покрытие гель-лаком', 1800, 90),
                ('Наращивание ногтей', 'Наращивание ногтей гелем или акрилом', 3500, 180),
                ('Дизайн ногтей', 'Художественный дизайн', 500, 30),
                ('Педикюр', 'Уход за стопами и ногтями ног', 3000, 120)
            ]
            cursor.executemany('INSERT INTO services (name, description, price, duration) VALUES (?, ?, ?, ?)',
                               services)

        # Добавляем администратора
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if cursor.fetchone()[0] == 0:
            admin_password = generate_password_hash('admin123')
            cursor.execute('''
                INSERT INTO users (username, password, role, full_name, phone, email) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', admin_password, 'admin', 'Администратор Салона', '+79990000000', 'admin@salon.ru'))

        # Добавляем мастеров
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "master"')
        if cursor.fetchone()[0] == 0:
            masters_data = [
                ('master1', 'master123', 'master', 'Елена Иванова', '+79990000001', 'elena@salon.ru'),
                ('master2', 'master123', 'master', 'Анна Петрова', '+79990000002', 'anna@salon.ru'),
                ('master3', 'master123', 'master', 'Мария Сидорова', '+79990000003', 'maria@salon.ru'),
            ]

            for username, password, role, full_name, phone, email in masters_data:
                hashed_password = generate_password_hash(password)
                cursor.execute('''
                    INSERT INTO users (username, password, role, full_name, phone, email) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, hashed_password, role, full_name, phone, email))

        conn.commit()


@app.route('/')
def index():
    # Главная страница доступна без авторизации
    conn = get_db_connection()
    services_list = conn.execute('SELECT * FROM services ORDER BY name').fetchall()
    masters_list = conn.execute('SELECT * FROM users WHERE role = "master" ORDER BY full_name').fetchall()
    conn.close()

    return render_template('index.html', services=services_list, masters=masters_list)


@app.route('/gallery')
def gallery():
    # Галерея работ доступна без авторизации
    return render_template('gallery.html')


@app.route('/about')
def about():
    # О салоне доступно без авторизации
    return render_template('about.html')


@app.route('/book_now')
def book_now():
    # Перенаправление на авторизацию при попытке записаться
    flash('Для записи на услугу необходимо войти в систему или зарегистрироваться', 'info')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        last_name = request.form['last_name']
        first_name = request.form['first_name']
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')

        # Собираем ФИО из фамилии и имени
        full_name = f"{last_name} {first_name}"

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO users (username, password, role, full_name, phone, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_password, 'client', full_name, phone, email))
            conn.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Имя пользователя уже существует', 'error')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Для доступа к панели управления необходимо войти в систему', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Статистика для разных ролей
    if session['role'] == 'client':
        # Клиент видит свои записи
        appointments = conn.execute('''
            SELECT a.*, s.name as service_name, u.full_name as master_name, s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users u ON a.master_id = u.id
            WHERE a.client_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['user_id'],)).fetchall()
    elif session['role'] == 'master':
        # Мастер видит свои записи
        appointments = conn.execute('''
            SELECT a.*, s.name as service_name, u.full_name as client_name, s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users u ON a.client_id = u.id
            WHERE a.master_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['user_id'],)).fetchall()
    else:
        # Администратор видит все записи
        appointments = conn.execute('''
            SELECT a.*, s.name as service_name, 
                   uc.full_name as client_name, 
                   um.full_name as master_name,
                   s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users uc ON a.client_id = uc.id
            JOIN users um ON a.master_id = um.id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''').fetchall()

    conn.close()

    return render_template('dashboard.html', appointments=appointments)


# Остальные маршруты остаются без изменений...
@app.route('/services')
def services():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    services_list = conn.execute('SELECT * FROM services ORDER BY name').fetchall()
    conn.close()

    return render_template('services.html', services=services_list)


@app.route('/masters')
def masters():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    masters_list = conn.execute('SELECT * FROM users WHERE role = "master" ORDER BY full_name').fetchall()
    conn.close()

    return render_template('masters.html', masters=masters_list)


@app.route('/new_appointment', methods=['GET', 'POST'])
def new_appointment():
    if 'user_id' not in session or session['role'] != 'client':
        flash('Только клиенты могут создавать записи', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        master_id = request.form['master_id']
        service_id = request.form['service_id']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        notes = request.form.get('notes', '')

        conn = get_db_connection()

        # Проверяем, свободно ли время у мастера
        existing_appointment = conn.execute('''
            SELECT * FROM appointments 
            WHERE master_id = ? AND appointment_date = ? AND appointment_time = ? AND status != "cancelled"
        ''', (master_id, appointment_date, appointment_time)).fetchone()

        if existing_appointment:
            flash('Это время уже занято. Выберите другое время.', 'error')
        else:
            conn.execute('''
                INSERT INTO appointments (client_id, master_id, service_id, appointment_date, appointment_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], master_id, service_id, appointment_date, appointment_time, notes))
            conn.commit()
            flash('Запись успешно создана!', 'success')
            return redirect(url_for('dashboard'))

        conn.close()

    conn = get_db_connection()
    masters = conn.execute('SELECT * FROM users WHERE role = "master" ORDER BY full_name').fetchall()
    services = conn.execute('SELECT * FROM services ORDER BY name').fetchall()
    conn.close()

    return render_template('new_appointment.html',
                           masters=masters,
                           services=services,
                           today=date.today().isoformat())


@app.route('/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Проверяем права доступа
    appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()

    if not appointment:
        flash('Запись не найдена', 'error')
    elif session['role'] == 'admin' or appointment['client_id'] == session['user_id']:
        conn.execute('UPDATE appointments SET status = "cancelled" WHERE id = ?', (appointment_id,))
        conn.commit()
        flash('Запись отменена', 'success')
    else:
        flash('У вас нет прав для отмены этой записи', 'error')

    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/complete_appointment/<int:appointment_id>')
def complete_appointment(appointment_id):
    if 'user_id' not in session or session['role'] not in ['admin', 'master']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()

    # Проверяем, что запись принадлежит мастеру (если это мастер)
    if session['role'] == 'master':
        appointment = conn.execute('SELECT * FROM appointments WHERE id = ? AND master_id = ?',
                                   (appointment_id, session['user_id'])).fetchone()
    else:
        appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (appointment_id,)).fetchone()

    if appointment:
        conn.execute('UPDATE appointments SET status = "completed" WHERE id = ?', (appointment_id,))
        conn.commit()
        flash('Запись отмечена как выполненная', 'success')
    else:
        flash('Запись не найдена или у вас нет прав', 'error')

    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/clients')
def clients():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    clients_list = conn.execute('SELECT * FROM users WHERE role = "client" ORDER BY full_name').fetchall()
    conn.close()

    return render_template('clients.html', clients=clients_list)


@app.route('/appointments')
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if session['role'] == 'admin':
        # Администратор видит все записи
        appointments_list = conn.execute('''
            SELECT a.*, s.name as service_name, 
                   uc.full_name as client_name, 
                   um.full_name as master_name,
                   s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users uc ON a.client_id = uc.id
            JOIN users um ON a.master_id = um.id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''').fetchall()
    elif session['role'] == 'master':
        # Мастер видит свои записи
        appointments_list = conn.execute('''
            SELECT a.*, s.name as service_name, u.full_name as client_name, s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users u ON a.client_id = u.id
            WHERE a.master_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['user_id'],)).fetchall()
    else:
        # Клиент видит свои записи
        appointments_list = conn.execute('''
            SELECT a.*, s.name as service_name, u.full_name as master_name, s.price
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            JOIN users u ON a.master_id = u.id
            WHERE a.client_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['user_id'],)).fetchall()

    conn.close()

    return render_template('appointments.html',
                           appointments=appointments_list,
                           today=date.today().isoformat())


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)