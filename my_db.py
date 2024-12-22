from flask_sqlalchemy import SQLAlchemy
import bcrypt 

db = SQLAlchemy()

class UserLogin(db.Model):
    __tablename__ = 'user_login'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_name = db.Column(db.String(255) )
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    rfid_card_id = db.Column(db.String(100), unique=True)
    is_admin = db.Column(db.Boolean, default=False)

    def __init__(self, user_name, password, name, email):
        self.user_name = user_name
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.name = name
        self.email = email

class Locker(db.Model):
    __tablename__ = 'lockers'
    id = db.Column(db.Integer, primary_key=True)
    locker_number = db.Column(db.Integer, unique=True)
    is_occupied = db.Column(db.Boolean, default=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user_login.id'), nullable=True)

def setup_database():
        db.create_all()        

def add_user(user_name, password, name, email):
        new_user = UserLogin(user_name=user_name, password=password, name=name, email=email)
        db.session.add(new_user)
        db.session.commit()

def get_user_by_email(email):
        return UserLogin.query.filter_by(email=email).first()

def delete_all_users():
        try:
                db.session.query(UserLogin).delete()
                db.session.commit()
        except Exception as e:
                print("Delete failed " +str(e))
                db.session.rollback()

def get_user_row_if_exists(id):
    user_row = UserLogin.query.filter_by(user_id=id).first()
    if user_row is not None:
        return user_row
    else:
        print(f"The user with id {id} does not exist")
        return False


def validate_user(email, password):
    user = UserLogin.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return {"status": "success", "message": "Login successful", "user": user}
    return {"status": "fail", "message": "Invalid email or password"}

def user_logout(id):
        row = get_user_row_if_exists(id)
        if row is not False:
         db.session.commit()
        
__all__ = ["UserLogin", "Locker", "db", "setup_database", "add_user", "get_user_by_email", "delete_all_users", "get_user_row_if_exists", "validate_user", "user_logout"]
