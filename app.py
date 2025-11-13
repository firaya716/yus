
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Замените на ваш секретный ключ

DATABASE = 'data1.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Таблица записей на маникюр
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            service TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Цены на услуги маникюра
prices = {
    'Маникюр классический': 1000,
    'Маникюр аппаратный': 1500,
    'Покрытие гель-лак': 1200,
    'Дизайн ногтей': 500,
}

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', prices=prices)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            flash('Пожалуйста, заполните все поля')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем уже существует!')
            return redirect(url_for('register'))
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = username
            flash('Успешный вход')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date'].strip()
        time_ = request.form['time'].strip()
        service = request.form['service']

        if not date or not time_ or not service:
            flash('Пожалуйста, заполните все поля для записи')
            return redirect(url_for('book'))

        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO appointments (user_id, date, time, service) VALUES (?, ?, ?, ?)
        ''', (session['user_id'], date, time_, service))
        conn.commit()
        conn.close()

        flash('Вы успешно записались на {} в {} {}'.format(service, date, time_))
        return redirect(url_for('index'))

    return render_template('book.html', prices=prices)

@app.route('/appointments')
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT date, time, service FROM appointments WHERE user_id = ? ORDER BY date, time', (session['user_id'],))
    appts = c.fetchall()
    conn.close()

    return render_template('appointments.html', appointments=appts)

if __name__ == '__main__':
    app.run(debug=True)
