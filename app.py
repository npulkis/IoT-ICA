
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, session
from flask_mysqldb import MySQL
from pubnub.pnconfiguration import PNConfiguration
from pubnub.callbacks import SubscribeCallback
from pubnub.pubnub import PubNub
from dotenv import load_dotenv
import os, re ,bcrypt, requests, json
import my_db
from datetime import timedelta
db= my_db.db


app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20) 
temporary_store = {}


load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE')
db.init_app(app)

pnconfig = PNConfiguration()
pnconfig.subscribe_key = os.getenv('PUBNUB_SUBSCRIBE_KEY')
pnconfig.publish_key = os.getenv('PUBNUB_PUBLISH_KEY')
pnconfig.user_id = os.getenv('PUBNUB_ID')
pnconfig.ssl = True
pubnub = PubNub(pnconfig)



def send_pubnub_message(channel, message):
    try:
        print(f"Sending message to {channel}: {message}")
        response = pubnub.publish().channel(channel).message(message).sync()
        if response.status.is_error():
            print(f"Error in PubNub publish: {response.status}")
        else:
            print(f"PubNub message sent: {response}")
    except Exception as e:
        print(f"PubNub publish failed: {e}")


@app.route("/", methods=["GET","POST"])
def index(): 
    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    lockers = my_db.Locker.query.all()

    if request.method == 'POST':
        locker_id = request.form.get('locker_id')
        action = request.form.get('action')

        locker = my_db.Locker.query.filter_by(id=locker_id).first()
        if not locker:
            flash('Locker not found.', 'danger')
            return redirect(url_for('dashboard'))

        if action == 'reserve':
            if locker.assigned_to is None:
                locker.is_occupied = True
                locker.assigned_to = user.id
                db.session.commit()

                send_pubnub_message("led_control", {"led_number": locker.locker_number, "action": "on"})
                flash(f'Locker {locker.locker_number} reserved successfully.', 'success')
            else:
                flash('Locker is already assigned to another user.', 'danger')

        elif action == 'unreserve':
            if locker.assigned_to == user.id:
                locker.is_occupied = False
                locker.assigned_to = None
                db.session.commit()

                send_pubnub_message("led_control", {"led_number": locker.locker_number, "action": "off"})
                flash(f'Locker {locker.locker_number} unreserved successfully.', 'success')
            else:
                flash('You can only unreserve lockers assigned to you.', 'danger')

    return render_template('dashboard.html', lockers=lockers, user=user)


@app.route('/toggle_locker', methods=['POST'])
def toggle_locker():
    if 'email' not in session:
        return jsonify({"status": "error", "message": "Please log in first."}), 403

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    locker_id = request.json.get('locker_id')
    locker = my_db.Locker.query.filter_by(id=locker_id, assigned_to=user.id).first()

    if not locker:
        return jsonify({"status": "error", "message": "Locker not found or not assigned to you."}), 403

    action = "off" if locker.is_occupied else "on"
    locker.is_occupied = not locker.is_occupied
    db.session.commit()

    send_pubnub_message("led_control", {"led_number": locker.locker_number, "action": action})

    return jsonify({"status": "success", "message": f"Locker {locker.locker_number} toggled {action}."})


@app.route('/reserve_locker', methods=['POST'])
def reserve_locker():
    if 'email' not in session:
        return jsonify({"status": "error", "message": "Please log in first."}), 403

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    locker_id = request.form.get('locker_id')
    locker = my_db.Locker.query.filter_by(id=locker_id, assigned_to=None).first()

    if locker:
        locker.assigned_to = user.id
        locker.is_occupied = True
        db.session.commit()
        flash(f"Locker {locker.locker_number} reserved successfully.", "success")
    else:
        flash("Locker is no longer available.", "danger")

    return redirect(url_for('dashboard'))


@app.route('/unreserve_locker', methods=['POST'])
def unreserve_locker():
    if 'email' not in session:
        return jsonify({"status": "error", "message": "Please log in first."}), 403

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    locker_id = request.form.get('locker_id')
    locker = my_db.Locker.query.filter_by(id=locker_id, assigned_to=user.id).first()

    if locker:
        locker.assigned_to = None
        locker.is_occupied = False
        db.session.commit()
        flash(f"Locker {locker.locker_number} unreserved successfully.", "success")
    else:
        flash("You cannot unreserve this locker.", "danger")

    return redirect(url_for('dashboard'))


@app.route('/set_mode', methods=['POST'])
def set_mode():
    data = request.json
    mode = data.get("mode")
    if mode not in ["register", "scan"]:
        return jsonify({"status": "error", "message": "Invalid mode"}), 400

    pubnub.publish().channel("mode_control").message({"mode": mode}).sync()
    return jsonify({"status": "success", "message": f"Mode set to {mode}"})



def send_led_command(led_number, action):
    message = {"led_number": led_number, "action": action}
    pubnub.publish().channel("led_control").message(message).sync()
    return {"status": "success", "message": f"LED {led_number} turned {action}"}

@app.route('/control_led', methods=['POST'])
def control_led():
    data = request.json
    led_number = data.get("led_number")
    action = data.get("action")
    if led_number and action in ["on", "off"]:
        return jsonify(send_led_command(led_number, action))
    return jsonify({"status": "error", "message": "Invalid input"}), 400

@app.route('/register_card', methods=['GET', 'POST'])
def register_card():
    if 'email' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if user.rfid_card_id:
            flash('RFID card already registered.', 'info')
            return redirect(url_for('select_locker'))

        temporary_store['current_email'] = session['email']

        flash('Please scan your card to register it.', 'info')
        return render_template('register_card.html')

    return render_template('register_card.html')

class CardRegistrationCallback(SubscribeCallback):
    def message(self, pubnub, message):
        data = message.message
        card_id = data.get("rfid_card_id")
        print(f"Received card ID for registration: {card_id}")

        with app.app_context():
            email = temporary_store.get('current_email')
            if not email:
                print("No email found in temporary store.")
                return

            user = my_db.UserLogin.query.filter_by(email=email).first()
            if user:
                user.rfid_card_id = card_id
                db.session.commit()
                print(f"Card {card_id} registered to user {user.name}.")
            else:
                print("No user found for card registration.")

class CardScanCallback(SubscribeCallback):
    def message(self, pubnub, message):
        data = message.message
        card_id = data.get("rfid_card_id")
        print(f"Received card ID for locker toggle: {card_id}")

        with app.app_context():
            user = my_db.UserLogin.query.filter_by(rfid_card_id=card_id).first()
            if not user:
                print("Card not registered.")
                return

            lockers = my_db.Locker.query.filter_by(assigned_to=user.id).all()
            if not lockers:
                print("No lockers assigned to this card.")
                return

            for locker in lockers:
                action = "off" if locker.is_occupied else "on"
                locker.is_occupied = not locker.is_occupied
                db.session.commit()

                send_pubnub_message("led_control", {"led_number": locker.locker_number, "action": action})
                print(f"Locker {locker.locker_number} toggled {action}")

pubnub.add_listener(CardRegistrationCallback())
pubnub.subscribe().channels("card_register").execute()

pubnub.add_listener(CardScanCallback())
pubnub.subscribe().channels("card_scan").execute()


@app.route('/select_locker', methods=['GET', 'POST'])
def select_locker():
    if 'email' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login'))

    user = my_db.UserLogin.query.filter_by(email=session['email']).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        locker_number = request.form['locker_number']
        locker = my_db.Locker.query.filter_by(locker_number=locker_number, is_occupied=False).first()
        if locker:
            locker.is_occupied = True
            locker.assigned_to = user.id
            db.session.commit()

            send_pubnub_message("led_control", {"led_number": locker_number, "action": "on"})
            flash(f'Locker {locker_number} assigned successfully!', 'success')
            return redirect(url_for('loggedin'))
        else:
            flash('Locker not available.', 'danger')

    available_lockers = my_db.Locker.query.filter_by(is_occupied=False).all()
    return render_template('select_locker.html', lockers=available_lockers)

@app.route('/scan_card', methods=['POST'])
def scan_card():
    card_id = request.json.get("rfid_card_id")
    if not card_id:
        return jsonify({"status": "error", "message": "Card ID is missing"}), 400

    user = my_db.UserLogin.query.filter_by(rfid_card_id=card_id).first()
    if not user:
        return jsonify({"status": "error", "message": "Card not registered"}), 404

    locker = my_db.Locker.query.filter_by(assigned_to=user.id).first()
    if not locker:
        return jsonify({"status": "error", "message": "No locker assigned to this card"}), 404

    action = "off" if locker.is_occupied else "on"
    locker.is_occupied = not locker.is_occupied
    db.session.commit()

    send_led_command(locker.locker_number, action)

    return jsonify({
        "status": "success",
        "message": f"Locker {locker.locker_number} toggled {action}"
    })


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
            return redirect(url_for('dashboard'))
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