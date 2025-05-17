from app import app
from flask import Flask, request, render_template, redirect, url_for, jsonify, json, current_app, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sshtunnel import SSHTunnelForwarder
from flask_wtf import FlaskForm
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from math import exp, log, log10, floor, sqrt
from datetime import datetime
from dotenv import load_dotenv
import random
import string
import hashlib
import zipfile
import stripe
import json
import xlwt
import csv
import os

load_dotenv()

stripe_keys = {
    "secret_key": os.getenv("STRIPE_SECRET_KEY"),
    "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY"),
    "endpoint_secret": os.getenv("STRIPE_ENPOINT_SECRET"),
}

stripe.api_key = stripe_keys["secret_key"]

# SSH Configuration
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

filedir =  os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(filedir, 'static')
domain = "https://www.urbanwaterways.org"

UPLOAD_FOLDER = filedir + "\\UPLOAD_FOLDER"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv("APP_SECRET_KEY")
# Uncomment when pulled in pythonanywhere
# app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{DB_NAME}"
# Keep uncommented when in localhost
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{LOCAL_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("APP_SECRET_KEY")

app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv("RECAPTCHA_SITE_KEY")
app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv("RECAPTCHA_SECRET_KEY")

db = SQLAlchemy()
db.init_app(app)

import app.models as models
import app.forms as forms

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))



# def do_sql(sql, values) -> list:
#     dba = sqlite3.connect(filedir + 'database.db')
#     cur = dba.cursor()
#     # If the value isn't none then the change will be commited to the database
#     if values is not None:
#         cur.execute(sql, values)
#         dba.commit()
#     else:  # If value is none then the changes will just be executed
#         cur.execute(sql)
#     return cur.fetchall()


# rounds num to sf number of s.f
def rounded(num, sf) -> float:
    return round(num, sf-int(floor(log10(abs(num))))-1)


def getConcentration(volume, mass) -> float:  # Calculates concentration
    return volume/mass


# main calculation function
def calculateRunoff(Area : float, ADD : float, INT : float, DUR : float, PH : float, Type : int) -> list:
    material = models.Surface_Material.query.filter_by(id=Type).first()
    # The variables below are named like that in the fomulas I was provided
    # TSS Coefficients
    a1 = material.a1
    a2 = material.a2
    a3 = material.a3
    a4 = material.a4
    a5 = material.a5
    a6 = material.a6
    a7 = material.a7
    a8 = material.a8
    a9 = material.a9
    # Cu Coefficients
    b1 = material.b1 
    b2 = material.b2
    b3 = material.b3 
    b4 = material.b4 
    b5 = material.b5 
    b6 = material.b6 
    b7 = material.b7 
    b8 = material.b8 
    g1 = material.g1
    # Zn Coefficients
    c1 = material.c1
    c2 = material.c2
    c3 = material.c3
    c4 = material.c4
    c5 = material.c5
    c6 = material.c6
    c7 = material.c7
    c8 = material.c8
    h1 = material.h1
    # Oter Coefficients
    Z  = material.Z
    k  = material.k
    l1 = material.l1
    m1 = material.m1

    surface = material.surface_type
    # Calculating water volume in litres
    volume = INT * Area * DUR

    # surface 1 is roof
    if surface == 1:
        # Calculate TSS roof
        if INT < 20:
            TSS = a1*(ADD**a2)*Area*(.75)*(1-exp(-k*INT*DUR))
        elif INT < 40:
            TSS = a1*(ADD**a2)*Area*(a3*INT+a4)*(1-exp(-k*INT*DUR))
        elif INT < 90:
            TSS = a1*(ADD**a2)*Area*(.91)*(1-exp(-k*INT*DUR))
        elif INT < 115:
            TSS = a1*(ADD**a2)*Area*(a5*INT+a6)*(1-exp(-k*INT*DUR))
        else:
            TSS = a1*(ADD**a2)*Area*(1)*(1-exp(-k*INT*DUR))
        TSS *= 1000

        # Calculating TCu roof
        Cu0 = (b1*PH**b2)*(b3*ADD**b4)*(b5*INT**b6)
        Cuest = b7*PH**b8
        K = (-log(Cuest/Cu0))/(INT*Z)
        if DUR < Z:
            TCu = Cu0*Area*(1/1000/K)*(1-exp(-K*INT*DUR))
        elif DUR >= Z:
            TCu = Cuest*Area*INT*(DUR-Z)+Cu0*Area*(1/1000/K)*(1-exp(-K*INT*Z))

        # Calculating TZn roof
        Zn0 = (c1*PH+c2)*(c3*ADD**c4)*(c5*INT**c6)
        Znest = c7*PH+c8
        K = (-log(Znest/Zn0))/(INT*Z)
        if DUR <= Z:
            TZn = Zn0*Area*(1/1000/K)*(1-exp(K*INT*DUR))
        elif DUR > Z:
            TZn = Znest*Area*INT*(DUR-Z)+Zn0*Area*1/1000/K*(1-exp(-K*INT*Z))

        # Calculating DCu roof
        DCu = l1*TCu

        # Calculating DZn roof
        DZn = m1*TZn

        # Surface 2 is road and 3 is carpark
    elif surface == 2 or surface == 3:
        # Calculating TSS road/carpark
        if INT < 40:
            TSS = a1*ADD**a2*Area*INT*(1-exp(-k*INT*DUR))
        elif INT < 90:
            TSS = Area*a1*ADD**a2*.50*(1-exp(-k*INT*DUR))
        elif INT < 130:
            TSS = Area*a1*ADD**a2*(a8*INT+a9)*(1-exp(-k*INT*DUR))
        elif INT >= 130:
            TSS = Area*a1*ADD**a2*1.00*(1-exp(-k*INT*DUR))
        # Calculating TCu road/carpark
        TCu = g1*TSS
        # Calculating TZn road/carpark
        TZn = h1*TSS
        # Calculating TCu road/carpark
        DCu = l1*TCu
        # Calculating TZn road/carpark
        DZn = m1*TZn
        # converting TSS from ug to mg
        TSS *= 1000

    # Calculations for concentration of runoff
    CTSS = TSS/volume
    CTCu = TCu/volume
    CTZn = TZn/volume
    CDCu = DCu/volume
    CDZn = DZn/volume
    flowRate = volume/DUR/60
    data = [TSS, TZn, DZn, TCu, DCu, volume,
            flowRate, CTSS, CTZn, CDZn, CTCu, CDCu]

    sigfig = 3
    # Rouds all data to 3 s.f
    for i in range(len(data)):
        data[i] = rounded(data[i], sigfig)
    return data


# function to convert csv file into data for graph and output csv
def csv_to_data(fileDir, Area, Type, surface) -> list:
    # Reads csv file and calculates
    with open(fileDir, newline='') as csvfile:
        graphData = [[], [], [], []]  # Data used for graph
        outputData = []  # Data used for output csv file
        fileReader = csv.reader(csvfile)
        fileLength = 0
        TSSTotal = 0
        TZnTotal = 0
        TCuTotal = 0
        for row in fileReader:
            if row[0].isnumeric():
                fileLength += 1
                # Calculates data
                runoff = calculateRunoff(Area, float(row[2]), float(row[3]),
                                         float(row[4]), float(row[1]), Type)
                try:
                    # If a date is provided then it will use the date instead of event number
                    graphData[0].append(row[5])
                    outputData.append([row[5], runoff])
                except:
                    # inserts what's in the first collum if no date
                    graphData[0].append(row[0])
                    outputData.append([row[0], runoff])
                # inserts the graph data
                graphData[1].append(runoff[0])
                graphData[2].append(runoff[1])
                graphData[3].append(runoff[3])
                # adds to the totals
                TSSTotal += runoff[0]
                TZnTotal += runoff[1]
                TCuTotal += runoff[3]

        # inserts a blank line into the csv
        outputData.append(['', ['']])
        # data for average runoff
        outputData.append(['Average:', [str(rounded(TSSTotal/fileLength, 5))+'mg',
                                        str(rounded(TZnTotal/fileLength, 5))+'mg',
                                        str(rounded(TCuTotal/fileLength, 5))+'mg']])
        # data for total runoff
        outputData.append(['Total:', [str(rounded(TSSTotal, 5))+'mg',
                                      str(rounded(TZnTotal, 5))+'mg',
                                      str(rounded(TCuTotal, 5))+'mg']])
        # blank line
        outputData.append(['', ['']])
        # input data
        outputData.append(['Area:', [str(Area)+'m2']])
        outputData.append(['Material:', [models.Surface_Material.query.filter_by(id=Type).first().name]])
        outputData.append(['Surface:', [get_surface_name(surface)]])

    return [graphData, outputData]


def check_file(filepath) -> bool:
    with open(filepath, newline='') as csvfile:
        fileReader = csv.reader(csvfile)
        try:
            for row in fileReader:
                if len(row) < 5 or len(row) > 6:  # checks number of collums is correct
                    return False
                for i in range(len(row)):
                    if row[i].isnumeric():  # checks if the data is numbers
                        if float(row[i]) <= 0:
                            return False
            return True
        except:
            return False


def data_to_csv(filepath, username, data):
    path = filedir + filepath + username + ".csv"
    zip_path = filedir + filepath + username + ".zip"
    make_filepath_avalable(path)

    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # sets the fileds for the top of the csv
        field = ['Event', 'TSS (mg)', 'TZn (mg)', 'DZn (mg)', 'TCu (mg)',
                 'DCu (mg)', 'Volume (l)', 'Flow rate (l/min)',
                 'Conc. TSS (mg/l)', 'Conc. TZn (mg/l)', 'Conc. DZn (mg/l)',
                 'Conc. TCu (mg/l)', 'Conc. DCu (mg/l)']
        writer.writerow(field)
        for i in data:
            # adds the data to the csv
            row = i[1]
            row.insert(0, i[0])
            writer.writerow(row)

    # zipFilepath = filedir + username + ".zip"

    # zip = zipfile.ZipFile(zipFilepath, "w", zipfile.ZIP_DEFLATED)
    # zip.write(filedir + filepath)
    # zip.close()
    # os.rename(filedir + zipFilepath, filedir + "static/output/" + zipFilepath)
    # os.remove(filedir + filepath)
    # os.remove(climateFilepath)


# retrns the material and the surface(roof, road, or carpark)
def get_surface() -> list:
    if request.form.get("roof_") == "on":
        Type = request.form['roof_type']
        surface = 1
    elif request.form.get("road_") == "on":
        Type = request.form['road_type']
        surface = 2
    elif request.form.get("carpark_") == "on":
        Type = request.form['carpark_type']
        surface = 3

    material = models.Surface_Material.query.filter_by(id=Type).first()
    if material.material_condition_type == 1: # if the material condition type is 1 i.e. is a parent material with a condition tab
        Type = request.form[str(Type)]  # the selection input is named after the parent id
    return [surface, Type]


# gets the name of the surface from surface as an int
def get_surface_name(surface) -> str:
    if surface == 1:
        return 'Roof'
    elif surface == 2:
        return 'Road'
    elif surface == 3:
        return 'Carpark'
    else:
        return 'Invalid'


def multi_surface_to_xlsl(climateFilepath : str, surfaceFilepath : str, username : str):
    print("calculating")
    climateData = []
    with open(climateFilepath, newline='') as climateCsvFile:
        climatecsvreader = csv.reader(climateCsvFile)
        for row in climatecsvreader:
             if row[1] != '' and row[1].isalpha() == False:
                climateData.append(row)
    wb = xlwt.Workbook()

    with open(surfaceFilepath, newline='') as surfaceCsvFile:
        surfaceCsvReader = csv.reader(surfaceCsvFile)

        sumamrySheet = wb.add_sheet("Summary")
        sumamrySheet.write(0, 0, "id")
        sumamrySheet.write(0, 1, "Surface")
        sumamrySheet.write(0, 2, "TSS Total(mg)")
        sumamrySheet.write(0, 3, "TSS Average(mg)")
        sumamrySheet.write(0, 4, "TSS Standard Deviation(mg)")
        sumamrySheet.write(0, 5, "TZn Total(mg)")
        sumamrySheet.write(0, 6, "TZn Average(mg)")
        sumamrySheet.write(0, 7, "TZn Standard Deviation(mg)")
        sumamrySheet.write(0, 8, "TCu Total(mg)")
        sumamrySheet.write(0, 9, "TCu Average(mg)")
        sumamrySheet.write(0, 10, "TCu Standard Deviation(mg)")
        rowNumber = 0
        for row in surfaceCsvReader:
            if not row[0].isnumeric() or not row[1].isnumeric() or int(row[0]) > 18:
                pass
            else:
                rowNumber += 1
                area = float(row[1])
                Type = int(row[0])
                TSSTotal = 0
                TSSVarience = 0
                TZnTotal = 0
                TZnVarience = 0
                TCuTotal = 0
                TCuVarience = 0

                sheetname = str(rowNumber)  # replace later
                ws = wb.add_sheet(sheetname, False)

                ws.write(0, 0, "Event")
                ws.write(0, 1, "TSS (mg)")
                ws.write(0, 2, "TZn (mg)")
                ws.write(0, 3, "DZn (mg)")
                ws.write(0, 4, "TCu (mg)")
                ws.write(0, 5, "DCu (mg)")
                ws.write(0, 6, "Volume (l)")
                ws.write(0, 7, "Flow rate (l/min)")
                ws.write(0, 8, "Conc. TSS (mg/l)")
                ws.write(0, 9, "Conc. TZn (mg/l)'")
                ws.write(0, 10, "Conc. DZn (mg/l)")
                ws.write(0, 11, "Conc. TCu (mg/l)")
                ws.write(0, 12, "Conc. DCu (mg/l)")

                ws.write(0, 15, "Average(mg)")
                ws.write(0, 16, "Total(mg)")
                ws.write(0, 17, "Standard Deviation(mg)")
                ws.write(1, 14, "TSS")
                ws.write(2, 14, "TZn")
                ws.write(3, 14, "TCu")

                ws.write(5, 15, "Surface:")
                ws.write(5, 16, models.Surface_Material.query.filter_by(id=Type).first().name)
                ws.write(6, 15, "Area:")
                ws.write(6, 16, area)

                for i in range(len(climateData)):
                    currentRow = i + 1
                    climateDataRow = climateData[i]
                    if len(climateDataRow) >= 6:
                        ws.write(currentRow, 0, climateDataRow[5])
                    else:
                        ws.write(currentRow, 0, currentRow)
                        pass
                                    
                    runoff = calculateRunoff(area,float(climateDataRow[2]), float(climateDataRow[3]),
                                            float(climateDataRow[4]), float(climateDataRow[1]),Type)
                    TSSTotal += runoff[0]
                    TZnTotal += runoff[1]
                    TCuTotal += runoff[3]
                    TSSVarience += (runoff[0]**2)/len(climateData)
                    TZnVarience += (runoff[0]**2)/len(climateData)
                    TCuVarience += (runoff[3]**2)/len(climateData)

                    for j in range(len(runoff)):
                        ws.write(currentRow, j+1, runoff[j])
                
                TSSAverage = TSSTotal/len(climateData)
                TZnAverage = TZnTotal/len(climateData)
                TCuAverage = TCuTotal/len(climateData)
                TSSVarience -= TSSAverage**2
                TZnVarience -= TZnAverage**2
                TCuVarience -= TCuAverage**2             

                TSSStandDev = sqrt(TSSVarience)
                TZnStandDev = sqrt(TZnVarience)
                TCuStandDev = sqrt(TCuVarience)

                ws.write(1, 15, TSSAverage)
                ws.write(1, 16, TSSTotal)
                ws.write(1, 17, TSSStandDev)
                ws.write(2, 15, TZnAverage)
                ws.write(2, 16, TZnTotal)
                ws.write(2, 17, TZnStandDev)
                ws.write(3, 15, TCuAverage)
                ws.write(3, 16, TCuTotal)
                ws.write(3, 17, TCuStandDev)

                sumamrySheet.write(rowNumber, 0, rowNumber)
                sumamrySheet.write(rowNumber, 1, models.Surface_Material.query.filter_by(id=Type).first().name)
                sumamrySheet.write(rowNumber, 2, TSSTotal)
                sumamrySheet.write(rowNumber, 3, TSSAverage)
                sumamrySheet.write(rowNumber, 4, TSSStandDev)
                sumamrySheet.write(rowNumber, 5, TZnTotal)
                sumamrySheet.write(rowNumber, 6, TZnAverage)
                sumamrySheet.write(rowNumber, 7, TZnStandDev)
                sumamrySheet.write(rowNumber, 8, TCuTotal)
                sumamrySheet.write(rowNumber, 9, TCuAverage)
                sumamrySheet.write(rowNumber, 10, TCuStandDev)

    filepath = username + ".xls"
    zipFilepath = username + ".zip"
    
    make_filepath_avalable(surfaceFilepath)
    make_filepath_avalable("app/static/output/" + zipFilepath)

    wb.save(filepath)
    zip = zipfile.ZipFile(zipFilepath, "w", zipfile.ZIP_DEFLATED)
    zip.write(filepath)
    zip.close()
    os.rename(zipFilepath, filedir + "app/static/output/" + zipFilepath)
    os.remove(filepath)

    return "static/output/" + zipFilepath


def make_filepath_avalable(filepath : str):
    try:
        # if there is already a prexisting file then remove it
        os.remove(filepath)
    except:
        print("no file")


# checks if the user is logged in
def check_login() -> bool:
    try:
        if current_user.username:
            return True
        else:
            return False
    except:
        return False


# checks the validity of the email
def check_email(email) -> bool:
    # checks if email has an @ then a . at least 1 character after the @
    at_index = None  # the index of the @
    for i in range(len(email)):
        if email[i] == "@" and i != 0:
            if at_index is not None:
                return False
            at_index = i
        if at_index is not None:
            if email[i] == "." and at_index+1 < i and len(email) >= i+1:
                return True
    return False


# check if the filename already exist for the user
def check_file_name(filename) -> bool:
    if check_login():
        # gets all user files where the file is 
        if filename == models.File_Data.query.filter(models.File_Data.users.any(id=current_user.id),
                                                      models.File_Data.name == filename).first():
            return False
        return True
    else:
        return False


def random_code(*, min_nupper = 3, ndigits = 3):
    letters_upper = random.choices(string.ascii_uppercase, k=min_nupper)
    digits = random.choices(string.digits, k=ndigits)

    password_chars = letters_upper + digits
    random.shuffle(password_chars)

    return ''.join(password_chars)


def send_email(recieving_email : str, subject : str, text : str, html : str):
    sender_email = "my@gmail.com"
    password = "Password"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recieving_email

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")


def send_reset_email(recieving_email : str) -> bool:  # returns wherther or not it worked
    pass


def Setup_data():
    # gets the materials and not the conditions of the materials e.g. poor, new
    roof_type = models.Surface_Material.query.filter(models.Surface_Material.surface_type==1, 
                                                     models.Surface_Material.material_condition_type!=2)
    road_type = models.Surface_Material.query.filter(models.Surface_Material.surface_type==2,
                                                      models.Surface_Material.material_condition_type!=2)
    carpark_type = models.Surface_Material.query.filter(models.Surface_Material.surface_type==3, 
                                                        models.Surface_Material.material_condition_type!=2)

    material_conditions = models.Surface_Material.query.filter_by(material_condition_type=2)

    material_condition_data = []
    # format: [[material_id, [[name, id], [name, id], [name, id]]],[material_id, [[name, id], [name, id], [name, id]]]
    for condition in material_conditions:
        condition_data = [condition.id, condition.name]

        material_already_added = False
        for i in material_condition_data:
            if i[0] == condition.condition_parent_id:
                material_already_added = True
                i[1].append(condition_data)
        
        if not material_already_added:
            material_condition_data.append([condition.condition_parent_id, [condition_data]])

    return [roof_type, road_type, carpark_type, material_condition_data]


def check_if_admin() -> bool:
    try:
        if current_user.administrator == 1:
            print('user is an admin')
            return True
        else:
            print('user isnt an admin')
            return False
    except:
        return False


def check_subscription() -> bool:
    if check_login():
        customer = models.Stripe_Customer.query.filter_by(user_id=current_user.id).first()
        if customer:
            try:
                session = stripe.checkout.Session.retrieve(customer.checkout_session_id, expand=["line_items"])
                subscription_id = session["subscription"]  # Access the subscription ID
                subscription = stripe.Subscription.retrieve(subscription_id)
                print(subscription.status)
                if subscription.status == 'active':
                    return True
            except stripe.error.StripeError as e:
                print(f"Error retrieving Checkout Session: {e}")
    return False


@app.route('/')
def Home_Page():
    admin = check_if_admin()
    return render_template('index.html', admin=admin, logged_in=check_login())


@app.route('/Multi_Event')
def Multi_Event():
    if check_login():  # if logged do the things
        if check_subscription():
            # gets the materials for each surface
            setupData = Setup_data()
            roof_type = setupData[0]
            road_type = setupData[1]
            carpark_type = setupData[2]
            condition_data = setupData[3]

            admin = check_if_admin()

            # gets all files uploaded from the user
            files = models.File_Data.query.filter(models.File_Data.users.any(id=current_user.id)).all()
            return render_template('Multi_Event.html', roof_type=roof_type,
                                files=files, road_type=road_type,
                                carpark_type=carpark_type,
                                condition_data=condition_data,
                                admin=admin,
                                logged_in=check_login())
        else:
            return redirect(url_for('Checkout'))
    else:  # not logged in then dont let user do multi event sim
        return render_template('needToLogin.html', logged_in=check_login())

@login_required
@app.route('/Single_Event', methods=['GET','POST'])
def Single_Event():

    form = forms.Single_Event()

    # gets the materials for each surface
    admin = check_if_admin()
    setupData = Setup_data()
    roof_type = setupData[0]
    road_type = setupData[1]
    carpark_type = setupData[2]
    condition_data = setupData[3]
    data = []
    # gets the surface based on which the material input
    error=False
    error_message=""
    if form.validate_on_submit():
        Type = get_surface()[1]
        try:
            # checks if pH is within acceptable range else throws error
            if form.pH.data > 7.1 or form.pH.data < 4:
                error=True
                error_message="pH isn't between 4 and 7.1"
            data = calculateRunoff(form.Area.data, form.ADD.data, form.INT.data, form.DUR.data, form.pH.data, Type)
            input_data = [get_surface_name(get_surface()[0]), form.Area.data, 
                          models.Surface_Material.query.filter_by(id=Type).first().name, 
                          form.ADD.data, form.INT.data, form.DUR.data, form.pH.data]
            return render_template('Single_Event.html', roof_type=roof_type,
                                admin=admin, form=form,
                                road_type=road_type, carpark_type=carpark_type,
                                input_data=input_data, data=data, output=True,
                                condition_data=condition_data,
                                logged_in=check_login())
        except:
            # if code breaks return error
            error = True
    else:
        print(form.errors)
    
    return render_template('Single_Event.html', roof_type=roof_type,
                        admin=admin, form=form,
                        road_type=road_type, carpark_type=carpark_type,
                        error=error, error_message=error_message,
                        condition_data=condition_data,
                        logged_in=check_login())


@app.route('/Multi_Event', methods=['POST'])
def Multi_Event_POST():
    if check_login():
        # variables for render template
        multiSurface = False
        setupData = Setup_data()
        roof_type = setupData[0]
        road_type = setupData[1]
        carpark_type = setupData[2]
        condition_data = setupData[3]
        graph = True
        file = None
        surface_file = None
        multi_surface = False
        error = False
        error_message = ""
        username = current_user.username

        admin = check_if_admin()
        #  Gats the name of the correct surface and type
        files = models.File_Data.query.filter(models.File_Data.users.any(id=current_user.id)).all()
        print(files)

        if request.form.get('Surface_file_') == 'on':
            multi_surface = True
            surface_csv = request.files['surface_csv']
            filename = secure_filename(surface_csv.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'surface_file_' + username)
            make_filepath_avalable(filepath)
            surface_csv.save(filepath)
            surface_file = filepath
        else:
            surface = get_surface()[0]
            Type = get_surface()[1]  # Type spesific type of the surface input

            Area = float(request.form['area'])
            if Area <= 0:
                error=True
                error_message = "Area has to be greater than 0"
        
        #  If file uploaded
        if request.form.get('file_') == 'on':
            file_name = request.form['file_name']
            csv = request.files['csv_input']
            filename = secure_filename(csv.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],
                                    str(random.randrange(9999999999)) +
                                    username + filename)
            csv.save(filepath)

            if not check_file_name(file_name):
                # error if file name exists under the current user
                error=True,
                error_message='File name already in use',

            if check_file(filepath):
                # if input file valid then asigns it for render template
                file = filepath
                #  Adds the filepath under the user in the database
                file_data = models.File_Data(upload_user_id=current_user.id, name=file_name, 
                                             path=filepath, public=False, time_uploaded=datetime.now())
                file_data.users.append(current_user)
                db.session.add(file_data)
                db.session.commit()

                
            else:
                #  If file isn't valid then delete it
                os.remove(filepath)
                error = True
                error_message = "Bad file input"
        else:
            file = request.form['location']

        # file would only be none if it isn't valid
        if file is not None and not error:
            #try:
            if multi_surface:
                
                input_data = ("1", "2", "3")
                graph_data = None
                output_data = multi_surface_to_xlsl(file, surface_file, username)
                graph = False
                multiSurface = True
            else:
                data = csv_to_data(file, Area, Type, surface)
                # data based on user input
                input_data = [get_surface_name(get_surface()[0]), Area, models.Surface_Material.query.filter_by(id=Type).first().name]
                graph_data = data[0]
                data_to_csv('\static\output\\', username, data[1])
                output_data = '\static\output\\' + username + ".csv"

            return render_template('Multi_Event.html', roof_type=roof_type,
                                   admin=admin, multiSurface=multiSurface,
                                   road_type=road_type, single_surface=True,
                                   condition_data=condition_data,
                                   carpark_type=carpark_type,
                                   input_data=input_data, graph=graph,
                                   output_file=output_data, files=files,
                                   graph_data=json.dumps(graph_data),
                                   logged_in=check_login())
        
        return render_template('Multi_Event.html', error=error,
                                   error_message=error_message,
                                   condition_data=condition_data,
                                   roof_type=roof_type, files=files,
                                   road_type=road_type,
                                   carpark_type=carpark_type,
                                   llogged_in=check_login())
    else:
        return render_template('needToLogin.html', logged_in=check_login())


@app.route('/Login', methods=['GET','POST'])
def Login():
    error = False
    admin = check_if_admin()
    form = forms.Login()
    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()
        if user:
            if hashlib.sha256(form.password.data.encode('utf-8')).hexdigest() == user.password:
                print(user.username,' Logged in')
                login_user(user, form.remember_me.data)
                return redirect(url_for('Home_Page'))
            error = True
    else:
        print(form.errors.items())
    return render_template('Login.html', admin=admin, logged_in=check_login(),form=form,error=error)


@app.route('/Logout', methods=['POST'])
def Logout():
    logout_user()
    return redirect(url_for('Home_Page'))


@app.route('/SignUp', methods=['GET','POST'])
def Sign_Up():
    form = forms.Register()

    error = False
    error_message = ""

    if form.validate_on_submit():
        existing_user_username = models.User.query.filter_by(
        username=form.username.data).first()
        if existing_user_username:
            error = True
            error_message = "That username already exists. Please chose another one."
        elif form.password.data != form.confirm_password.data:
            error = True
            error_message = "Passwords do not match."
        elif len(form.password.data) < 8:
            error = True
            error_message = "Password must be at least 8 characters long."
        elif len(form.username.data) < 1:
            error = True
            error_message = "Username must be at least 1 character long."
        elif not check_email(form.email.data):
            error = True
            error_message = "Invalid email"
        if not error:    
            hashed_password = hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()
            new_user = models.User(username=form.username.data, password=hashed_password, 
                                   email=form.email.data, date_joined=datetime.now(), name=form.name.data)
            db.session.add(new_user)
            db.session.commit()
            print("Signup")
            login_user(new_user, False)
            return redirect(url_for('Dashboard'))
        else:
            print(error_message)
    else:
        print(form.errors, " Form Error")
    admin = check_if_admin()
    return render_template('SignUp.html', error=error, logged_in=check_login(),
                           admin=admin, form=form, error_message=error_message)


@app.route('/Privacy_Policy')
def PrivacyPolicy():
    admin=check_if_admin()
    return render_template('Privacy_policy.html', logged_in=check_login(),
                           admin=admin)


@app.route('/Checkout')
def Checkout():
    admin=check_if_admin()
    if check_login():
        return render_template('checkout.html', logged_in=check_login(),
                           admin=admin)
    else:
        return redirect(url_for('Home_Page'))


@app.route('/Success')
def Success():
    admin=check_if_admin()
    return render_template('success.html', logged_in=check_login(),
                           admin=admin)


@app.route('/Cancelled')
def Cancelled():
    admin=check_if_admin()
    return render_template('cancel.html', logged_in=check_login(),
                           admin=admin)


@app.route('/Dashboard')
def Dashboard():
    admin=check_if_admin()
    files = models.File_Data.query.filter_by(upload_user_id=current_user.id).all()
    print(files, current_user, "123")
    check_subscription()
    return render_template('Dashboard.html', logged_in=check_login(),
                           admin=admin, user=current_user, uploaded_files=files)


@app.route('/Admin')
def Admin():
    admin = check_if_admin()

    users = models.User.query.filter_by(administrator = 0)
    print(users)
    return render_template('Admin.html', logged_in=check_login(), 
                           admin=admin, users=users)


@app.route("/config")
def get_publishable_key():
    stripe_config = {"publicKey": stripe_keys["publishable_key"]}
    return jsonify(stripe_config)


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        prices = stripe.Price.list(
            lookup_keys=[request.form['lookup_key']],
            expand=['data.product']
        )

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': prices.data[0].id,
                    'quantity': 1,
                },
            ],
            client_reference_id=current_user.id,
            customer_email=current_user.email,
            mode='subscription',
            success_url=domain +
            '/Success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain + '/Cancelled',
        )
        
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        print(e)
        return "Server error", 500
    

@app.route('/create-portal-session', methods=['POST'])
def customer_portal():
    # This is the URL to which the customer will be redirected after they are
    # done managing their billing with the portal.
    return_url = domain + '/Dashboard'
    
    customer = models.Stripe_Customer.query.filter_by(user_id=current_user.id).first()
    print(customer)
    if customer:
        portalSession = stripe.billing_portal.Session.create(
            customer=customer.stripe_customer_id,
            return_url=return_url,
        )
        return redirect(portalSession.url, code=303)
    else:
        return "Server error", 500


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_keys["endpoint_secret"]
        )
    
    except ValueError as e:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":        
        stripe_session = event["data"]["object"]
        Handle_Payment(stripe_session)

    return "Success", 200


def Handle_Payment(stripe_session):
    client_reference_id = stripe_session.get('client_reference_id')
    stripe_customer_id = stripe_session["customer"]
    customer = models.Stripe_Customer.query.filter_by(user_id=client_reference_id).first()
    print("Payment was successful.",customer)
    if customer:
        customer.stripe_subscription_id = stripe_session["id"]
    else:
        customer = models.Stripe_Customer(user_id=client_reference_id, checkout_session_id = stripe_session["id"],
                                          stripe_customer_id=stripe_customer_id)
        db.session.add(customer)
    db.session.commit()
        


@app.errorhandler(404)  # 404 page
def Page_Not_Found(error):
    print(error)
    admin=check_if_admin()
    return render_template('404page.html', logged_in=check_login(),
                           admin=admin)


@app.errorhandler(500)
def Server_error(error):
    print(error)
    admin=check_if_admin()
    return render_template('500 page', logged_in=check_login(),
                           admin=admin)