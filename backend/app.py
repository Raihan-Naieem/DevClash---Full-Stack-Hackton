# all the imports
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, SelectField, IntegerField, BooleanField, TimeField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests, re, os, enum
import enum
from dotenv import load_dotenv
from util import SQL


load_dotenv()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, '../frontend/templates')
STATIC_FOLDER = os.path.join(BASE_DIR, '../frontend/static')

app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)



app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')



# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# User class that Flask-Login needs
class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    user_row = SQL('SELECT * FROM users WHERE id = ?', user_id)
    if user_row is None:
        return None
    return User(id_=user_row[0]['id'], username=user_row[0]['username'])



# Forms
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    user_type = SelectField('Account Type', choices=[('student', 'Student'), ('vendor', 'Vendor')], default='student')
    shop_name = StringField('Shop Name')
    
    def validate_email(self, email):
        if self.user_type.data == 'student':
            pattern = r'^[a-zA-Z0-9._%+-]+@(student\.)?cuet\.ac\.bd$' # magic regX code from ai
            if not re.match(pattern, email.data):
                raise ValidationError('Please use a valid CUET email address.')
        
        user = SQL('SELECT * FROM users WHERE email = ? ', email.data)
        if user:
            raise ValidationError('Email already registered.')
        
        
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.route("/", methods=['GET','POST'])
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    user_type = request.args.get('type', 'student')
    form.user_type.data = user_type  # optional pre-fill

    if form.validate_on_submit():
        email = form.email.data
        password = generate_password_hash(form.password.data or "")

 
        SQL('''
            INSERT INTO users (email, password_hash, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', email, password)

        # Get the ID of the newly inserted user
        user = SQL('SELECT id FROM users WHERE email = ?', email)
        user_id = user[0]['id']

        if user_type == 'student':
            SQL('INSERT INTO students (user_id) VALUES (?)', user_id)
        elif user_type == 'vendor':
            SQL('''
                INSERT INTO vendors (user_id, availability, schedule)
                VALUES (?, ?, ?)
            ''', user_id, None)  # Default values: pending, available, no schedule
        else:
            flash("Invalid user type!", "danger")
            return render_template("register.html", form=form, user_type=user_type)

        flash("Registration successful!", "success")
        return redirect(url_for('login'))
    

    return render_template("register.html", form=form, user_type=user_type)



if __name__ == '__main__':

    SQL("PRAGMA foreign_keys = ON;")

    SQL('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    SQL('''
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')

    SQL('''
        CREATE TABLE IF NOT EXISTS vendors (
            user_id INTEGER PRIMARY KEY,
            availability INTEGER CHECK(availability IN (0, 1)),
            schedule DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')


    SQL('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            name TEXT,
            price REAL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(vendor_id) REFERENCES vendors(user_id) ON DELETE CASCADE
        );
    ''')

    SQL('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            vendor_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('pending', 'preparing', 'ready')),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(user_id) ON DELETE CASCADE
        );
    ''')

    SQL('''
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER,
            item_id INTEGER,
            quantity INTEGER NOT NULL,
            PRIMARY KEY (order_id, item_id),
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
        );
    ''')

    SQL('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT,
            FOREIGN KEY(student_id) REFERENCES students(user_id) ON DELETE CASCADE,
            FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
    ''')
    app.run(host='0.0.0.0', debug=True)

