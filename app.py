import os
import base64
from datetime import datetime, timedelta
import io
import matplotlib
import matplotlib.pyplot as plt
import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

matplotlib.use('Agg')

# Usuń istniejącą bazę danych
if os.path.exists('users.db'):
    os.remove('users.db')

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class CurrencyRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Float, nullable=False)

class CovidData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    active_cases = db.Column(db.Integer, nullable=False)
    total_cases = db.Column(db.Integer, nullable=False)
    total_deaths = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your username and/or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard/currencies', methods=['GET', 'POST'])
@login_required
def currencies():
    if request.method == 'POST':
        api_url = "http://api.nbp.pl/api/exchangerates/tables/A?format=json"
        response = requests.get(api_url)
        if response.status_code == 200:
            currencies_data = response.json()
            top_10_currencies = currencies_data[0]['rates'][:10]
        else:
            top_10_currencies = []
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d')
        historical_data = {}

        for currency in top_10_currencies:
            code = currency['code']
            history_url = f"http://api.nbp.pl/api/exchangerates/rates/A/{code}/{start_date}/{end_date}/?format=json"
            history_response = requests.get(history_url)
            if history_response.status_code == 200:
                history = history_response.json()
                rates = [rate['mid'] for rate in history['rates']]
                dates = [rate['effectiveDate'] for rate in history['rates']]
                historical_data[code] = {'rates': rates, 'dates': dates}

                for date, rate in zip(dates, rates):
                    existing_rate = CurrencyRate.query.filter_by(code=code, date=date).first()
                    if not existing_rate:
                        new_rate = CurrencyRate(code=code, date=date, rate=rate)
                        db.session.add(new_rate)
                db.session.commit()
        
        top_10_currencies.sort(key=lambda x: x['mid'], reverse=True)

        plots = {}
        for currency in top_10_currencies:
            code = currency['code']
            data = historical_data[code]
            plt.figure(figsize=(5, 3))
            plt.plot(data['dates'], data['rates'], marker='o')
            plt.title(f'{code} to PLN (Last 31 Days)')
            plt.xlabel('Date')
            plt.ylabel('Rate')
            plt.xticks(rotation=45)
            plt.tight_layout()

            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            plots[code] = base64.b64encode(img.getvalue()).decode('utf8')
            plt.close()
        
        return render_template('currencies.html', currencies=top_10_currencies, plots=plots)
    
    return render_template('currencies.html', currencies=[], plots={})

@app.route('/dashboard/covid', methods=['GET', 'POST'])
@login_required
def covid():
    countries = {
        "Poland": "POL",
        "Germany": "DEU",
        "Russia": "RUS",
        "China": "CHN",
        "USA": "USA",
        "France": "FRA"
    }
    api_url = "https://covid-api.com/api/reports"
    target_date = "2023-01-01"

    for country_name, iso_code in countries.items():
        response = requests.get(api_url, params={"iso": iso_code, "date": target_date})
        if response.status_code == 200 and 'data' in response.json() and len(response.json()['data']) > 0:
            covid_data = response.json()['data']
            
            # Sumuj dane dla wszystkich prowincji
            total_active_cases = sum([data['active'] for data in covid_data])
            total_cases = sum([data['confirmed'] for data in covid_data])
            total_deaths = sum([data['deaths'] for data in covid_data])
            
            existing_data = CovidData.query.filter_by(date=target_date, country=country_name).first()
            if existing_data:
                existing_data.active_cases = total_active_cases
                existing_data.total_cases = total_cases
                existing_data.total_deaths = total_deaths
            else:
                new_data = CovidData(
                    date=target_date,
                    country=country_name,
                    active_cases=total_active_cases,
                    total_cases=total_cases,
                    total_deaths=total_deaths
                )
                db.session.add(new_data)
            db.session.commit()
    
    covid_records = CovidData.query.filter_by(date=target_date).all()
    
    # Generowanie wykresu słupkowego
    countries = [record.country for record in covid_records]
    deaths = [record.total_deaths for record in covid_records]

    plt.figure(figsize=(10, 6))
    plt.bar(countries, deaths, color='red')
    plt.xlabel('Country')
    plt.ylabel('Total Deaths')
    plt.title('COVID-19 Total Deaths on 2023-01-01')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    
    return render_template('covid.html', covid_records=covid_records, plot_url=plot_url)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=True)