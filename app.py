
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, session
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import os, re ,bcrypt, requests, json
import my_db
from datetime import timedelta
db= my_db.db


app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)



load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE')
db.init_app(app)



@app.route("/", methods=["GET","POST"])
def index(): 
    return redirect(url_for('login'))



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_name = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, email):
            flash('Invalid email address. Please enter a valid email.', 'danger')
            return render_template('signup.html')

        if not re.fullmatch(r'^(?=.*[A-Z])(?=.*\d).{8,}$', password):
            flash('Password must be at least 8 characters long, contain at least one digit, and one uppercase letter.', 'danger')
            return render_template('signup.html')
        
        existing_user = my_db.get_user_by_email(email)
        if existing_user:
            flash('Email already registered. Please choose a different email.', 'danger')
            return render_template('signup.html')

        my_db.add_user(user_name=user_name, name=name, password=password, email=email)
        flash('You have successfully signed up!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = my_db.get_user_by_email(email)
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session.permanent = True
            session['email'] = user.email
            session['name'] = user.name
            session['user_name'] = user.user_name
            flash('Login successful!', 'success')
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html')

@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route('/loggedin')
def loggedin():
    if 'email' in session:
        return f'Email:{session["email"]}, Username:{session["user_name"]}, Name:{session["name"]}!'
    else:
        return redirect(url_for('login'))
    
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)