from app import app
from flask import Flask, request, render_template, session, redirect, url_for, jsonify, json, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from math import exp, log, log10, floor, sqrt
import random
import string
import hashlib
import zipfile
import stripe
import json
import xlwt
import csv
import os

stripe_keys = {
    "secret_key": "sk_test_51QEKXbASoVcyVGhrVn85dRlBcFTOLwkFjXrce6BCyzYIhQoN92EUNCPgkmXcMfl3JGDgK9OhjUeBnZqjg1jXS6cO00gpwYzXCf",
    "publishable_key": "pk_test_51QEKXbASoVcyVGhr4P0zhYDur1yO2BazoOhUkmhvWAGSm9meP3VbzuzbvmV32cHyaoNXE6isvUPdC3RrrHBx4bHL00QyqwfOE9",
    "endpoint_secret": "whsec_8a53777483939cc643b64281e1e59fff728d15cb78cbf4fbdfbab074bc2ae49c",
}

stripe.api_key = stripe_keys["secret_key"]


# This bellow is just for ease of use with pythonanywhere
filedir =  os.path.abspath(os.path.dirname(__file__))
#domain = 'http://localhost:4242'
domain = "http://127.0.0.1:4242/"
UPLOAD_FOLDER = filedir + "UPLOAD_FOLDER"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = b'1fK#F92m1,-{l1,maw:>}an79&*#^%n678&*'  # No looking
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(filedir, "database.db")
app.config['SECRET_KEY'] = '1fK#F92m1,-{l1,maw:>}an79&*#^%n678&*'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True)
    password = db.Column(db.String(200))
    email = db.Column(db.String(254))



class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(max=25)])
    email = StringField(validators=[InputRequired(), Length(max=254)])    
    password = PasswordField(validators=[InputRequired(), Length(max=50)])
    confirm_password = PasswordField(validators=[InputRequired(), Length(max=50)])
    
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
         max=25)], render_kw={"placeholder": "Username"})
    
    password = PasswordField(validators=[InputRequired(), Length(
        max=50)], render_kw={"placeholder": "Password"})
    
    submit = SubmitField("Login")


def do_sql(sql, values) -> list:
    dba = sqlite3.connect(filedir + 'database.db')
    cur = dba.cursor()
    # If the value isn't none then the change will be commited to the database
    if values is not None:
        cur.execute(sql, values)
        dba.commit()
    else:  # If value is none then the changes will just be executed
        cur.execute(sql)
    return cur.fetchall()


# rounds num to sf number of s.f
def rounded(num, sf) -> float:
    return round(num, sf-int(floor(log10(abs(num))))-1)


def getConcentration(volume, mass) -> float:  # Calculates concentration
    return volume/mass


# main calculation function
def calculateRunoff(Area : float, ADD : float, INT : float, DUR : float, PH : float, Type : int) -> list:
    coeff = do_sql("SELECT * FROM Coefficient WHERE id='{}';".format(Type), None)
    # The variables below are named like that in the fomulas I was provided
    # TSS Coefficients
    a1 = coeff[0][3]
    a2 = coeff[0][4]
    a3 = coeff[0][5]
    a4 = coeff[0][6]
    a5 = coeff[0][7]
    a6 = coeff[0][8]
    a7 = coeff[0][9]
    a8 = coeff[0][10]
    a9 = coeff[0][11]

    # Cu Coefficients
    b1 = coeff[0][13]
    b2 = coeff[0][14]
    b3 = coeff[0][15]
    b4 = coeff[0][16]
    b5 = coeff[0][17]
    b6 = coeff[0][18]
    b7 = coeff[0][19]
    b8 = coeff[0][20]
    g1 = coeff[0][22]

    # Zn Coefficients
    c1 = coeff[0][24]
    c2 = coeff[0][25]
    c3 = coeff[0][26]
    c4 = coeff[0][27]
    c5 = coeff[0][28]
    c6 = coeff[0][29]
    c7 = coeff[0][30]
    c8 = coeff[0][31]
    h1 = coeff[0][32]

    # Other Coefficients
    Z = coeff[0][21]
    k = coeff[0][12]
    l1 = coeff[0][23]
    m1 = coeff[0][33]

    surface = coeff[0][34]
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
        outputData.append(['Material:', [get_material_name(Type)]])
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

    material = do_sql("SELECT * FROM Coefficient WHERE id = '{}';".format(Type), None)
    if material[0][35] == 1: # if the material condition type is 1 i.e. is a parent material with a condition tab
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


# gets the id of the surface(road roof carpark) from type (galvanised, ect)
def get_surface_from_type(typeInt : str, typeStr : str, isInt : bool) -> int:
    if isInt:
        surface = do_sql("SELECT type FROM Coefficient WHERE id = '{}'".format(typeInt), None)
        return surface[0][0]
    else:
        surface = do_sql("SELECT type FROM Coefficient WHERE name = '{}'".format(typeStr), None)
        return surface[0][0]



# gats the name of the material fron material as an int
def get_material_name(material) -> str:
    mat = do_sql("SELECT name FROM Coefficient WHERE id = '{}';".format(material), None)
    return mat[0][0]


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
        num_of_surfaces = number_of_surfaces()
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
                ws.write(5, 16, get_material_name(Type))
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
                sumamrySheet.write(rowNumber, 1, get_material_name(Type))
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
    make_filepath_avalable("static/output/" + zipFilepath)

    wb.save(filepath)
    zip = zipfile.ZipFile(zipFilepath, "w", zipfile.ZIP_DEFLATED)
    zip.write(filepath)
    zip.close()
    os.rename(zipFilepath, filedir + "static/output/" + zipFilepath)
    os.remove(filepath)

    return "static/output/" + zipFilepath


def number_of_surfaces() -> int:
    surfaces = do_sql("SELECT * FROM Coefficient;", None)
    return len(surfaces)


def make_filepath_avalable(filepath : str):
    try:
        # if there is already a prexisting file then remove it
        os.remove(filepath)
    except:
        print("no file")


# checks if the user is logged in
def check_login() -> bool:
    try:
        if session['username']:
            return True
        else:
            return False
    except:
        return False


# login text to tell user if logged in or not
def get_login_text() -> str:
    if check_login():
        return 'Logout'
    else:
        return 'Login'


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
        # gets all file names for user
        userFileNames = do_sql('''SELECT File_data.name FROM File_data,User
                           Where File_data.user_id = User.id
                           And User.username = "{}";'''.format(session['username']), None)
        for i in userFileNames:
            if i[0] == filename:  # check if the name is taken
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
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1 AND material_condition_type != 2;", None)
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2 AND material_condition_type != 2;", None)
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3 AND material_condition_type != 2;", None)

    material_conditions = do_sql("SELECT * FROM Coefficient WHERE material_condition_type = 2;", None)

    material_condition_data = []
    # format: [[material_id, [[name, id], [name, id], [name, id]]],[material_id, [[name, id], [name, id], [name, id]]]]
    for condition in material_conditions:
        parent_material_id = condition[36]
        coefficient_id = condition[0]
        condition_name = condition[2]
        condition_data = [coefficient_id, condition_name]

        material_already_added = False
        for i in material_condition_data:
            if i[0] == parent_material_id:
                material_already_added = True
                i[1].append(condition_data)
        
        if not material_already_added:
            material_condition_data.append([parent_material_id, [condition_data]])

    return [roof_type, road_type, carpark_type, material_condition_data]


def check_if_admin() -> bool:
    try:
        username = session['username']
        value = do_sql('''SELECT administrator FROM User WHERE username="{}";'''.format(username), None)
        if value[0][0] == 1:
            return True
        else:
            return False
    except:
        return False


@app.route('/')
def Home_Page():
    admin = check_if_admin()
    print(User.query.all())
    return render_template('index.html', admin=admin, login_text=get_login_text())


@app.route('/Multi_Event')
def Multi_Event():
    if check_login():  # if logged do the things
        # gets the materials for each surface
        setupData = Setup_data()
        roof_type = setupData[0]
        road_type = setupData[1]
        carpark_type = setupData[2]
        condition_data = setupData[3]
        username = session['username']

        admin = check_if_admin()

        # gets all files uploaded from the user
        files = do_sql('''SELECT File_data.name, File_data.path FROM File_data, User WHERE
                       File_data.file_type=1 and File_data.user_id=User.id and
                       User.username="{}";'''.format(username), None)
        return render_template('Multi_Event.html', roof_type=roof_type,
                               files=files, road_type=road_type,
                               carpark_type=carpark_type,
                               condition_data=condition_data,
                               admin=admin,
                               login_text=get_login_text())
    else:  # not logged in then dont let user do multi event sim
        return render_template('needToLogin.html', login_text=get_login_text())


@app.route('/Single_Event')
def Single_Event():

    admin = check_if_admin()

    # gets the materials for each surface
    setupData = Setup_data()
    roof_type = setupData[0]
    road_type = setupData[1]
    carpark_type = setupData[2]
    condition_data = setupData[3]
    return render_template('Single_Event.html', roof_type=roof_type,
                           admin=admin,
                           road_type=road_type, carpark_type=carpark_type,
                           condition_data=condition_data,
                           login_text=get_login_text())


@app.route('/Single_Event', methods=['POST'])
def Single_Event_POST():
    # gets the materials for each surface
    admin = check_if_admin()
    setupData = Setup_data()
    roof_type = setupData[0]
    road_type = setupData[1]
    carpark_type = setupData[2]
    condition_data = setupData[3]
    data = []
    surface = get_surface()[0]
    Type = get_surface()[1]
    # gets the surface based on which the material input
    surface_n_type = do_sql("""SELECT Coefficient.name, Site_type.name
                            FROM Coefficient,Site_type WHERE
                            Coefficient.type=Site_type.id and
                            Coefficient.id='{}'""".format(int(Type)), None)

    try:
        # geting all of the input variables
        Area = float(request.form['area'])
        ADD = float(request.form['ADD'])
        INT = float(request.form['INT'])
        DUR = float(request.form['DUR'])
        PH = float(request.form['PH'])
        # checks if pH is within acceptable range else throws error
        if PH > 7.1 or PH < 4:
            return render_template('Single_Event.html', roof_type=roof_type,
                                   admin=admin,
                                   road_type=road_type, carpark_type=carpark_type,
                                   error=True, error_message="pH isn't between 4 and 7.1",
                                   login_text=get_login_text())
        single = True  # bool for if output
        data = calculateRunoff(Area, ADD, INT, DUR, PH, Type)
        input_data = [surface_n_type[0][1], Area, surface_n_type[0][0], ADD, INT, DUR, PH]
        return render_template('Single_Event.html', roof_type=roof_type,
                               admin=admin,
                               road_type=road_type, carpark_type=carpark_type,
                               input_data=input_data, data=data, single=single,
                               condition_data=condition_data,
                               login_text=get_login_text())
    except:
        # if code breaks return error
        return render_template('Single_Event.html', roof_type=roof_type,
                               admin=admin,
                               road_type=road_type, carpark_type=carpark_type,
                               error=True, error_message="Invalid data",
                               condition_data=condition_data,
                               login_text=get_login_text())


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

        username = session['username']

        admin = check_if_admin()
        #  Gats the name of the correct surface and type
        files = do_sql('''SELECT File_data.name, File_data.path FROM File_data,
                       User WHERE File_data.file_type=1 and
                       File_data.user_id=User.id and
                       User.username="{}";'''.format(username), None)

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

            surface_n_type = do_sql("""SELECT Coefficient.name, Site_type.name FROM
                        Coefficient,Site_type WHERE
                        Coefficient.type=Site_type.id and
                        Coefficient.id='{}'""".format(int(Type)), None)
            try:
                Area = float(request.form['area'])
            except:
                # if area is broken then return error
                return render_template('Multi_Event.html', error=True,
                                    admin=admin,
                                    error_message='Invalid data',
                                    condition_data=condition_data,
                                    roof_type=roof_type,
                                    files=files,
                                    road_type=road_type,
                                    carpark_type=carpark_type,
                                    login_text=get_login_text())
            if Area <= 0:
                return render_template('Multi_Event.html', error=True,
                                    admin=admin,
                                    error_message="Area can't be less than or equal to  0",
                                    condition_data=condition_data,
                                    roof_type=roof_type, files=files,
                                    road_type=road_type,
                                    carpark_type=carpark_type,
                                    login_text=get_login_text())
        
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
                return render_template('Multi_Event.html', error=True,
                                       admin=admin,
                                       error_message='File name already used',
                                       condition_data=condition_data,
                                       roof_type=roof_type, files=files,
                                       road_type=road_type,
                                       carpark_type=carpark_type,
                                       login_text=get_login_text())

            if check_file(filepath):
                # if input file valid then asigns it for render template
                file = filepath
                #  Adds the filepath under the user in the database
                userId = do_sql('''SELECT id FROM User WHERE
                                username="{}"'''.format(username), None)
                do_sql('''INSERT INTO File_data (name, path, file_type,
                       user_id) VALUES (?,?,?,?);''',
                       (file_name, filepath, 1, userId[0][0]))
            else:
                #  If file isn't valid then delete it
                os.remove(filepath)
        else:
            file = request.form['location']

        # file would only be none if it isn't valid
        if file is not None:
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
                input_data = [surface_n_type[0][1], Area, surface_n_type[0][0]]
                graph_data = data[0]
                data_to_csv("static/output/", username, data[1])
                output_data = "/static/output/" + username + ".csv"

            return render_template('Multi_Event.html', roof_type=roof_type,
                                   admin=admin, multiSurface=multiSurface,
                                   road_type=road_type, single_surface=True,
                                   condition_data=condition_data,
                                   carpark_type=carpark_type,
                                   input_data=input_data, graph=graph,
                                   output_file=output_data, files=files,
                                   graph_data=json.dumps(graph_data),
                                   login_text=get_login_text())
            
#            except:
#                # returns error if anything breaks
#                return render_template('Multi_Event.html', error=True,
#                                       error_message='File Error',
#                                       roof_type=roof_type, files=files,
#                                       road_type=road_type,
#                                       carpark_type=carpark_type,
#                                       login_text=get_login_text())
        else:
            #  Throws an error if there is a problem with the file
            return render_template('Multi_Event.html', error=True,
                                   error_message='File Error',
                                   condition_data=condition_data,
                                   roof_type=roof_type, files=files,
                                   road_type=road_type,
                                   carpark_type=carpark_type,
                                   login_text=get_login_text())
    else:
        return render_template('needToLogin.html', login_text=get_login_text())


@app.route('/Login')
def Login():
    admin = check_if_admin()
    form = LoginForm()
    return render_template('Login.html', admin=admin, login_text=get_login_text(),form=form)


@app.route('/Login', methods=['GET','POST'])
def Login_Post():

    admin = check_if_admin()
    username = request.form['username']
    # encrypted and hashed password
    password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
    users = do_sql('SELECT * FROM User', None)
    for user in users:
        if str(username) == str(user[1]) and str(password) == str(user[2]):
            # sets session to username if correct user input and redirects
            session['username'] = username
            return redirect(url_for('Home_Page'))
    return render_template('Login.html', error=True, login_text=get_login_text(),
                           admin=admin,)


@app.route('/SignUp', methods=['GET','POST'])
def Sign_Up():
    form = RegisterForm()

    error = False
    error_message = ""

    if form.validate_on_submit():
        existing_user_username = User.query.filter_by(
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
            error_message = "Password must be at least 1 character long."
        elif not check_email(form.email.data):
            error = True
            error_message = "Invalid email"
        if not error:    
            hashed_password = hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()
            print(len(hashed_password))
            new_user = User(username=form.username.data, password=hashed_password, email=form.email.data)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('Home_Page'))
        else:
            print(error_message)
        
    admin = check_if_admin()
    return render_template('SignUp.html', error=error, login_text=get_login_text(),
                           admin=admin, form=form, error_message=error_message)

'''
@app.route('/SignUp', methods=['POST'])
def Sign_Up_Post():
    # get user inputs
    admin = check_if_admin()
    username = request.form['username']
    password = request.form['password']
    redoPassword = request.form['redoPassword']
    email = request.form['email']

    unavalableUsernames = do_sql('SELECT username FROM User;', None)

    # username length constraint is 6
    if len(username) < 6:
        print("username too short")
        return render_template('SignUp.html', error=True, username_error=True,
                               admin=admin,
                               error_message="Username has to be at least 6 characters",
                               login_text=get_login_text())

    # if username is taken then throw error
    for name in unavalableUsernames:
        if username == name[0]:
            print("unavalable username")
            return render_template('SignUp.html', error=True,
                                   username_error=True,
                                   admin=admin,
                                   error_message="Username already exists",
                                   login_text=get_login_text())

    # if email isnt a valid emain then throw error
    if not check_email(email):
        print("Invalid email address")
        return render_template('SignUp.html', error=True, email_error=True,
                               admin=admin,
                               error_message="Invalid email address",
                               login_text=get_login_text())

    # if password is too short then throw error
    if len(password) < 8:
        print('password too short')
        return render_template('SignUp.html', error=True, password_error=True,
                               admin=admin,
                               error_message="Password is less than 8 characters",
                               login_text=get_login_text())

    # if passwords do not match then throw error
    if redoPassword != password:
        print("non matching passwords")
        return render_template('SignUp.html', error=True, password_error=True,
                               admin=admin,
                               error_message="Passwords do not match",
                               login_text=get_login_text())

    # if it gets past all of the constraints then insert the data
    # insert the hashed and encrypted version of the password
    do_sql('INSERT INTO User (username,password,email) VALUES (?,?,?);',
           (username, hashlib.sha256(password.encode('utf-8')).hexdigest(), email))

    # log in the user and redirect to home
    session['username'] = username
    return redirect(url_for('Home_Page'))
'''

@app.route('/Privacy_Policy')
def PrivacyPolicy():
    admin=check_if_admin()
    return render_template('Privacy_policy.html', login_text=get_login_text(),
                           admin=admin)


@app.route('/Checkout')
def Checkout():
    admin=check_if_admin()
    if check_login():
        return render_template('checkout.html', login_text=get_login_text(),
                           admin=admin)
    else:
        return redirect(url_for('Home_Page'))


@app.route('/Success')
def Success():
    admin=check_if_admin()
    return render_template('success.html', login_text=get_login_text(),
                           admin=admin)


@app.route('/Cancelled')
def Cancelled():
    admin=check_if_admin()
    return render_template('cancel.html', login_text=get_login_text(),
                           admin=admin)



@app.route('/Admin')
def Admin():
    admin = check_if_admin()

    users = do_sql('''SELECT username,email,id FROM User WHERE administrator=0;''', None)
    print(users)
    return render_template('Admin.html', login_text=get_login_text(), \
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
    # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
    # Typically this is stored alongside the authenticated user in your database.
    checkout_session_id = request.form.get('session_id')
    checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)

    # This is the URL to which the customer will be redirected after they are
    # done managing their billing with the portal.
    return_url = domain

    portalSession = stripe.billing_portal.Session.create(
        customer=checkout_session.customer,
        return_url=return_url,
    )
    return redirect(portalSession.url, code=303)


# @app.route('/webhook', methods=['POST'])
# def webhook_received():
#     # Replace this endpoint secret with your endpoint's unique secret
#     # If you are testing with the CLI, find the secret by running 'stripe listen'
#     # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
#     # at https://dashboard.stripe.com/webhooks
#     webhook_secret = stripe_keys['secret_key']
#     request_data = json.loads(request.data)

#     if webhook_secret:
#         # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
#         signature = request.headers.get('stripe-signature')
#         try:
#             event = stripe.Webhook.construct_event(
#                 payload=request.data, sig_header=signature, secret=webhook_secret)
#             data = event['data']
#         except Exception as e:
#             return e
#         # Get the type of webhook event sent - used to check the status of PaymentIntents.
#         event_type = event['type']
#     else:
#         data = request_data['data']
#         event_type = request_data['type']
#     data_object = data['object']

#     print('event ' + event_type)

#     if event_type == 'checkout.session.completed':
#         print('🔔 Payment succeeded!')
#     elif event_type == 'customer.subscription.trial_will_end':
#         print('Subscription trial will end')
#     elif event_type == 'customer.subscription.created':
#         print('Subscription created %s', event.id)
#     elif event_type == 'customer.subscription.updated':
#         print('Subscription created %s', event.id)
#     elif event_type == 'customer.subscription.deleted':
#         # handle subscription canceled automatically based
#         # upon your subscription settings. Or if the user cancels it.
#         print('Subscription canceled: %s', event.id)
#     elif event_type == 'entitlements.active_entitlement_summary.updated':
#         # handle active entitlement summary updated
#         print('Active entitlement summary updated: %s', event.id)

#     return jsonify({'status': 'success'})

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
        print("Payment was successful.")
        print(session['username'] )
        # TODO: run some custom code here

    return "Success", 200

@app.errorhandler(404)  # 404 page
def Page_Not_Found(error):
    admin=check_if_admin()
    return render_template('404page.html', login_text=get_login_text(),
                           admin=admin)


@app.errorhandler(500)
def Server_error(error):
    admin=check_if_admin()
    return render_template('500 page', login_text=get_login_text(),
                           admin=admin)