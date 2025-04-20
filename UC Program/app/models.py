from flask_login import UserMixin

from app.routes import db

User_File = db.Table('User_file',
    db.Column('user_id', db.Integer, db.ForeignKey('User.id')),
    db.Column('file_id', db.Integer, db.ForeignKey('File_data.id'))
)

class User(db.Model, UserMixin):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(25), unique=True)
    password = db.Column(db.String(200))
    email = db.Column(db.String(254))
    administrator = db.Column(db.Integer, default=0)
    date_joined = db.Column(db.String(35))
    files = db.relationship('File_Data', secondary = User_File, back_populates = 'users')

class File_Data(db.Model):
    __tablename__ = "File_data"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    path = db.Column(db.String(100))
    time_uploaded = db.Column(db.String(100))
    description = db.Column(db.String(300))
    public = db.Column(db.Integer)
    downloads = db.Column(db.Integer)
    upload_user_id = db.Column(db.Integer, db.ForeignKey('User.id'))
    users = db.relationship('User', secondary = User_File, back_populates = 'files')

class Stripe_Customer(db.Model):
    __tablename__ = "Stripe_Customer"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))
    stripe_customer_id = db.Column(db.String(255), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=False)

class Surface_Material(db.Model):
    __tablename__ = "Coefficient"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    surface_type = db.Column(db.Integer)
    material_condition_type = db.Column(db.Integer)
    condition_parent_id = db.Column(db.Integer, db.ForeignKey('Coefficient.id'))
    # TSS Coefficients
    a1 = db.Column(db.Integer)
    a2 = db.Column(db.Integer)
    a3 = db.Column(db.Integer)
    a4 = db.Column(db.Integer)
    a5 = db.Column(db.Integer)
    a6 = db.Column(db.Integer)
    a7 = db.Column(db.Integer)
    a8 = db.Column(db.Integer)
    a9 = db.Column(db.Integer)
    # Cu Coefficients
    b1 = db.Column(db.Integer)
    b2 = db.Column(db.Integer)
    b3 = db.Column(db.Integer)
    b4 = db.Column(db.Integer)
    b5 = db.Column(db.Integer)
    b6 = db.Column(db.Integer)
    b7 = db.Column(db.Integer)
    b8 = db.Column(db.Integer)
    g1 = db.Column(db.Integer)
    # Zn Coefficients
    c1 = db.Column(db.Integer)
    c2 = db.Column(db.Integer)
    c3 = db.Column(db.Integer)
    c4 = db.Column(db.Integer)
    c5 = db.Column(db.Integer)
    c6 = db.Column(db.Integer)
    c7 = db.Column(db.Integer)
    c8 = db.Column(db.Integer)
    h1 = db.Column(db.Integer)
    # Oter Coefficientss
    Z  = db.Column(db.Integer)
    k  = db.Column(db.Integer)
    l1 = db.Column(db.Integer)
    m1 = db.Column(db.Integer)