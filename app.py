from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import matplotlib
matplotlib.use('Agg')  # Ustawienie backendu Matplotlib na "Agg"
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
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
        # Pobieranie danych z API NBP
        api_url = "http://api.nbp.pl/api/exchangerates/tables/A?format=json"
        response = requests.get(api_url)
        if response.status_code == 200:
            currencies_data = response.json()
            top_10_currencies = currencies_data[0]['rates'][:10]
        else:
            top_10_currencies = []
        
        # Pobieranie danych historycznych dla każdej waluty
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

                # Zapisanie danych do bazy danych, jeśli nie istnieją
                for date, rate in zip(dates, rates):
                    existing_rate = CurrencyRate.query.filter_by(code=code, date=date).first()
                    if not existing_rate:
                        new_rate = CurrencyRate(code=code, date=date, rate=rate)
                        db.session.add(new_rate)
                db.session.commit()
        
        # Generowanie wykresów
        plots = {}
        for code, data in historical_data.items():
            plt.figure(figsize=(5, 3))  # Pomniejszenie wykresów
            plt.plot(data['dates'], data['rates'], marker='o')
            plt.title(f'{code} to PLN (Last 31 Days)')
            plt.xlabel('Date')
            plt.ylabel('Rate')
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Zapisanie wykresu do stringa w formacie base64
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            plots[code] = base64.b64encode(img.getvalue()).decode('utf8')
            plt.close()
        
        return render_template('currencies.html', currencies=top_10_currencies, plots=plots)
    
    return render_template('currencies.html', currencies=[], plots={})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Uruchomienie aplikacji na określonym adresie IP i porcie
    app.run(host='0.0.0.0', port=5000, debug=True)