from flask_login import UserMixin

from app.routes import db


class User(db.Model, UserMixin):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True)
    password = db.Column(db.String(200))
    email = db.Column(db.String(254))