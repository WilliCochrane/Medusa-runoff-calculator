from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
import os

Base = declarative_base()

load_dotenv()

SSH_HOST = 'ssh.pythonanywhere.com'
SSH_USERNAME = 'willicochrane'
SSH_PASSWORD = os.getenv("SSH_PASSWORD")

DB_USER = 'willicochrane'
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = 'willicochrane$MEDUSAdb'
REMOTE_DB_HOST = f'{SSH_USERNAME}.mysql.pythonanywhere-services.com'
REMOTE_DB_PORT = 3306

# Set up the SSH tunnel
tunnel = SSHTunnelForwarder(
    (SSH_HOST, 22),
    ssh_username=SSH_USERNAME,
    ssh_password=SSH_PASSWORD,
    remote_bind_address=(REMOTE_DB_HOST, REMOTE_DB_PORT)
)

tunnel.start()
LOCAL_PORT = tunnel.local_bind_port

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30))
    username = Column(String(25), unique=True)
    password = Column(String(200))
    email = Column(String(254))
    administrator = Column(Integer, default=0)
    date_joined =  Column( String(35))

class File_Data(Base):
    __tablename__ = "File_data"
    id =  Column( Integer, primary_key=True, autoincrement=True)
    name =  Column( String(100))
    path =  Column( String(100))
    time_uploaded =  Column( String(100))
    description =  Column( String(300))
    public =  Column( Integer)
    downloads =  Column( Integer)
    upload_user_id =  Column( Integer,  ForeignKey('User.id'))

class Stripe_Customer(Base):
    __tablename__ = "Stripe_Customer"
    id = Column( Integer, primary_key=True, autoincrement=True)
    user_id = Column( Integer,  ForeignKey('User.id'))
    stripe_customer_id =  Column( String(255), nullable=False)
    checkout_session_id =  Column( String(255), nullable=False)

class Surface_Material(Base):
    __tablename__ = "Coefficient"
    id =  Column( Integer, primary_key=True, autoincrement=True)
    site =  Column( String(100))
    name =  Column( String(100))
    surface_type =  Column( Integer)
    material_condition_type =  Column( Integer)
    condition_parent_id =  Column( Integer,  ForeignKey('Coefficient.id'))
    # TSS Coefficients
    a1 =  Column( Integer)
    a2 =  Column( Integer)
    a3 =  Column( Integer)
    a4 =  Column( Integer)
    a5 =  Column( Integer)
    a6 =  Column( Integer)
    a7 =  Column( Integer)
    a8 =  Column( Integer)
    a9 =  Column( Integer)
    # Cu Coefficients
    b1 =  Column( Integer)
    b2 =  Column( Integer)
    b3 =  Column( Integer)
    b4 =  Column( Integer)
    b5 =  Column( Integer)
    b6 =  Column( Integer)
    b7 =  Column( Integer)
    b8 =  Column( Integer)
    g1 =  Column( Integer)
    # Zn Coefficients
    c1 =  Column( Integer)
    c2 =  Column( Integer)
    c3 =  Column( Integer)
    c4 =  Column( Integer)
    c5 =  Column( Integer)
    c6 =  Column( Integer)
    c7 =  Column( Integer)
    c8 =  Column( Integer)
    h1 =  Column( Integer)
    # Oter Coefficientss
    Z  =  Column( Integer)
    k  =  Column( Integer)
    l1 =  Column( Integer)
    m1 =  Column( Integer)

class User_File(Base):
    __tablename__ = "User_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('User.id'))
    file_id = Column(Integer, ForeignKey('File_data.id'))

filedir =  os.path.abspath(os.path.dirname(__file__))+"/app"
sqlite_engine = create_engine('sqlite:///' + os.path.join(filedir, "database.db"))

mysql_engine = create_engine( f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{LOCAL_PORT}/{DB_NAME}")

SQLite_Session = sessionmaker(bind=sqlite_engine)
sqlite_session = SQLite_Session()


MySQL_Session = sessionmaker(bind=mysql_engine)
mysql_session = MySQL_Session()

#Base.metadata.create_all(mysql_engine)

for table in [User, File_Data, Stripe_Customer, Surface_Material, User_File]:
    records = sqlite_session.query(table).all()
    for record in records:
        mysql_session.merge(record)

#mysql_session.commit()
print("Done")
sqlite_session.close()
mysql_session.close()