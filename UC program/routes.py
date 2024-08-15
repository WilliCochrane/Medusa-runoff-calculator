from flask import Flask, request, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from math import exp, log, log10, floor
import sqlite3
import csv
import json
import os
import random

#filedir = "/home/willicochrane/"
filedir = ""

app = Flask(__name__,static_folder=filedir+"static")
UPLOAD_FOLDER = filedir + "UPLOAD_FOLDER"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = b'1fK#F92m1,-{l1,maw:>}an79&*#^%n678&*'


def do_sql(sql, values):
    db = sqlite3.connect('Coefficients.db')
    cur = db.cursor()
    if values != None:
        cur.execute(sql, values)
        db.commit()
    else:
        cur.execute(sql)
    return cur.fetchall()


def rounded(num, sf):
    return round(num, sf-int(floor(log10(abs(num))))-1)


def getConcentration(volume, mass):
    return volume/mass


def calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface):
    coeff = do_sql("SELECT * FROM Coefficient WHERE id='{}'".format(int(Type)), None)
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

        # TSS *= 1000

    CTSS = TSS/volume
    CTCu = TCu/volume
    CTZn = TZn/volume
    CDCu = DCu/volume
    CDZn = DZn/volume
    flowRate = volume/DUR/60

    data = [TSS, TZn, DZn, TCu, DCu, volume, flowRate, CTSS, CTZn, CDZn, CTCu, CDCu]
    sigfig = 5
    
    for i in range(len(data)):
        data[i] = rounded(data[i], sigfig)
    return data


def csv_to_data(fileDir, Area, Type, surface):
    with open(fileDir, newline='') as csvfile:
        graphData = [[], [], [], []]
        outputData = []
        fileReader = csv.reader(csvfile)
        for row in fileReader:
            if row[0].isnumeric():
                runoff = calculateRunoff(Area, float(row[2]), float(row[3]),
                                         float(row[4]), float(row[1]), Type, surface)
                try:
                    graphData[0].append(row[5])
                    outputData.append([row[5], runoff])
                except:
                    graphData[0].append(row[0])
                    outputData.append([row[0], runoff])
                graphData[1].append(runoff[0])
                graphData[2].append(runoff[1])
                graphData[3].append(runoff[3])
                
    return [graphData, outputData]


def check_file(filepath):
    with open(filepath, newline='') as csvfile:
        fileReader = csv.reader(csvfile)
        try:
            for row in fileReader:
                if len(row) < 5 or len(row) > 6:
                    return False
                for i in range(len(row)):
                    if row[i].isnumeric():
                        if float(row[i]) <= 0:
                            return False
            return True
        except:
            return False


def data_to_csv(filepath, username, data):
    path = filedir + filepath + username + ".csv"
    try:
        os.remove(path)
    except:
        print("no file")

    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        field = ['Event', 'TSS (mg)', 'TZn (mg)', 'DZn (mg)', 'TCu (mg)', 'DCu (mg)', 'Volume (l)', 'Flow rate (l/min)', 
                 'Conc. TSS (mg/l)', 'Conc. TZn (mg/l)', 'Conc. DZn (mg/l)', 'Conc. TCu (mg/l)', 'Conc. DCu (mg/l)']
        writer.writerow(field)
        for i in data:
            row = i[1]
            row.insert(0, i[0])
            writer.writerow(row)


def get_surface():
    if request.form.get("roof_") == "on":
        Type = request.form['roof_type']
        surface = 1
    elif request.form.get("road_") == "on":
        Type = request.form['road_type']
        surface = 2
    elif request.form.get("carpark_") == "on":
        Type = request.form['carpark_type']
        surface = 3
    return [surface, Type]


def get_user_data(username):
    userFiles = do_sql('''SELECT * FROM File_data Where File_data.id = User_File_data.File_data_id AND
                       User_File_data.User_id = User.id And User.username = {}'''.format(username), None) 
    print(userFiles)
    return userFiles


def check_email(email):
    has_at = False
    for i in email:
        if i == "@":
            has_at = True
        elif i == "." and has_at:
            return True
    return False


@app.route('/')
def Home_Page():
    return render_template('Home.html')


@app.route('/Calculator')
def Calc_Form():
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
    return render_template('index.html', roof_type=roof_type,
                           road_type=road_type,
                           carpark_type=carpark_type)


@app.route('/Calculator', methods=['POST'])
def Calc_Form_Post():
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
    Area = float(request.form['area'])
    graph = False
    single = False
    data = []
    surface = get_surface()[0]
    Type = get_surface()[1]

    surface_n_type = do_sql("""SELECT Coefficient.name, Site_type.name FROM Coefficient,Site_type WHERE 
                            Coefficient.type=Site_type.id and Coefficient.id='{}'""".format(int(Type)), None)

    # Single event simulation
    if int(request.form['event']) == 2:
        ADD = float(request.form['ADD'])
        INT = float(request.form['INT'])
        DUR = float(request.form['DUR'])
        PH = float(request.form['PH'])
        single = True
        data = calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface)
        input_data = [surface_n_type[0][1], Area, surface_n_type[0][0], ADD, INT, DUR, PH]

        return render_template('index.html', roof_type=roof_type, road_type=road_type, 
                               carpark_type=carpark_type, input_data=input_data,
                               data=data, single=single, graph=graph)

    # Full year simulation
    elif int(request.form['event']) == 1:
        graph = True
        file = filedir + "static/climate_data/climate_events_2011_CCC.csv"
        surface = get_surface()[0]
        Type = get_surface()[1]
        try:
            username = session['username']
        except:
            username = str(random.randint(100000000,999999999))

        if request.form.get('file_') == 'on':
            csv = request.files['csv_input']
            filename = secure_filename(csv.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            csv.save(filepath)
            if check_file(filepath):
                file = filepath
            else:
                os.remove(filepath)
        else:
            file = filedir + "static/climate_data/" + request.form['location']
        
        data = csv_to_data(file, Area, Type, surface)
        input_data = [surface_n_type[0][1], Area, surface_n_type[0][0]]
        graph_data = data[0]

        data_to_csv("static/output/", username, data[1])
        output_data = "/static/output/" + username + ".csv"
        return render_template('index.html', roof_type=roof_type, road_type=road_type, 
                               carpark_type=carpark_type, input_data=input_data,
                               graph=graph, single=single, output_file=output_data,
                               graph_data=json.dumps(graph_data))


@app.route('/Login')
def Login():
    return render_template('Login.html')


@app.route('/Login', methods=['POST'])
def Login_Post():
    session['username'] = request.form['username']
    return render_template('Login.html')


@app.route('/SignUp')
def Sign_Up():
    return render_template('SignUp.html', error=False)


@app.route('/SignUp', methods=['POST'])
def Sign_Up_Post():
    username = request.form['username']
    password = request.form['password']
    redoPassword = request.form['redoPassword']
    email = request.form['email']

    unavalableUsernames = do_sql('SELECT username FROM User;', None)
    for name in unavalableUsernames:
        if username == name[0]:
            print("unavalable username")
            return render_template('SignUp.html', error=True, username_error=True, error_message="Unavalable username")

    if not check_email(email):
        print("Invalid email address")
        return render_template('SignUp.html', error=True, email_error=True, error_message="Invalid email address")

    if redoPassword != password:
        print("non matching passwords")
        return render_template('SignUp.html', error=True, password_error=True, error_message="Passwords do not match")
    

    print(username, password, redoPassword, email)
    do_sql('INSERT INTO User (username,password,email) VALUES (?,?,?);', (username, password, email))
    return redirect(url_for('Home_Page'))


@app.errorhandler(404)  # 404 page
def Page_Not_Found(error):
    return render_template('404page.html')


if __name__ == "__main__":  # Last lines
    app.run(debug=True)
