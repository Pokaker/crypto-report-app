from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import json
import os
import hashlib
import requests
import csv
from io import StringIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

USERS_FILE = 'users.json'

COINS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
    "cardano": "Cardano (ADA)",
    "ripple": "Ripple (XRP)",
    "dogecoin": "Dogecoin (DOGE)",
}

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        users = load_users()

        if email in users and users[email] == hash_password(password):
            session['email'] = email
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        users = load_users()

        if email in users:
            flash('Пользователь с таким email уже существует', 'danger')
        else:
            users[email] = hash_password(password)
            save_users(users)
            flash('Регистрация прошла успешно! Теперь войдите.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', email=session.get('email'))

@app.route('/get_data', methods=['POST'])
def get_data():
    if 'email' not in session:
        return redirect(url_for('login'))

    coin = request.form.get('coin')
    days = int(request.form.get('days'))

    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
        prices_data = raw_data.get('prices', [])

        data = []
        dates = []
        prices = []

        for item in prices_data:
            timestamp = item[0]
            price = item[1]
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
            data.append({"date": date_str, "price": round(price, 2)})
            dates.append(date_str)
            prices.append(round(price, 2))

        coin_name = COINS.get(coin, coin)

        session['last_data'] = data
        session['last_coin_name'] = coin_name
        session['last_days'] = days

        return render_template('dashboard.html',
                             email=session['email'],
                             data=data,
                             dates=dates,
                             prices=prices,
                             coin_name=coin_name,
                             days=days)

    except Exception as e:
        flash(f'Ошибка при получении данных: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/download_csv')
def download_csv():
    if 'email' not in session or 'last_data' not in session:
        flash('Нет данных для скачивания', 'warning')
        return redirect(url_for('dashboard'))

    data = session.get('last_data', [])
    coin_name = session.get('last_coin_name', 'Crypto')
    days = session.get('last_days', 7)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Дата', 'Цена USD'])
    
    for item in data:
        writer.writerow([item['date'], item['price']])

    output.seek(0)
    filename = f"{coin_name.split()[0]}_{days}days.csv"

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)