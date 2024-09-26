from flask import Flask, request, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from math import exp, log, log10, floor
from random import randrange
import hashlib
import sqlite3
import csv
import json
import os

# This bellow is just for ease of use with pythonanywhere
# filedir = "/home/willicochrane/"
filedir = ""

app = Flask(__name__, static_folder=filedir+"static")
UPLOAD_FOLDER = filedir + "UPLOAD_FOLDER"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = b'1fK#F92m1,-{l1,maw:>}an79&*#^%n678&*'  # No looking


def do_sql(sql, values) -> list:
    db = sqlite3.connect('Coefficients.db')
    cur = db.cursor()
    # If the value isn't none then the change will be commited to the database
    if values is not None:
        cur.execute(sql, values)
        db.commit()
    else:  # If value is none then the changes will just be executed
        cur.execute(sql)
    return cur.fetchall()


# rounds num to sf number of s.f
def rounded(num, sf) -> float:
    return round(num, sf-int(floor(log10(abs(num))))-1)


def getConcentration(volume, mass) -> float:  # Calculates concentration
    return volume/mass


# main calculation function
def calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface) -> list:
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
    sigfig = 5
    # Rouds all data to 5 s.f
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
                                         float(row[4]), float(row[1]), Type,
                                         surface)
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
    try:
        # if there is already a prexisting file then remove it
        os.remove(path)
    except:
        print("no file")

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


# gats the name of the material fron material as an int
def get_material_name(material) -> str:
    mat = do_sql("SELECT name FROM Coefficient WHERE id = '{}';".format(material), None)
    return mat[0][0]


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


@app.route('/')
def Home_Page():
    return render_template('index.html', login_text=get_login_text())


@app.route('/Multi_Event')
def Multi_Event():
    if check_login():  # if logged do the things
        # gets the materials for each surface
        roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
        road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
        carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
        username = session['username']
        # gets all files uploaded from the user
        files = do_sql('''SELECT File_data.name, File_data.path FROM File_data, User WHERE
                       File_data.file_type=1 and File_data.user_id=User.id and
                       User.username="{}";'''.format(username), None)
        return render_template('Multi_Event.html', roof_type=roof_type,
                               files=files, road_type=road_type,
                               carpark_type=carpark_type,
                               login_text=get_login_text())
    else:  # not logged in then dont let user do multi event sim
        return render_template('needToLogin.html', login_text=get_login_text())


@app.route('/Single_Event')
def Single_Event():
    # gets the materials for each surface
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
    return render_template('Single_Event.html', roof_type=roof_type,
                           road_type=road_type, carpark_type=carpark_type,
                           login_text=get_login_text())


@app.route('/Single_Event', methods=['POST'])
def Single_Event_POST():
    # gets the materials for each surface
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
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
                                   road_type=road_type, carpark_type=carpark_type,
                                   error=True, error_message="pH isn't between 4 and 7.1",
                                   login_text=get_login_text())

        single = True  # bool for if output
        data = calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface)
        input_data = [surface_n_type[0][1], Area, surface_n_type[0][0], ADD, INT, DUR, PH]

        return render_template('Single_Event.html', roof_type=roof_type,
                               road_type=road_type, carpark_type=carpark_type,
                               input_data=input_data, data=data, single=single,
                               login_text=get_login_text())
    except:
        # if code breaks return error
        return render_template('Single_Event.html', roof_type=roof_type,
                               road_type=road_type, carpark_type=carpark_type,
                               error=True, error_message="Invalid data",
                               login_text=get_login_text())


@app.route('/Multi_Event', methods=['POST'])
def Multi_Event_POST():
    if check_login():
        # variables for render template
        roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1", None)
        road_type = do_sql("SELECT * FROM Coefficient WHERE type=2", None)
        carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3", None)
        surface = get_surface()[0]
        Type = get_surface()[1]
        graph = True
        file = None
        surface = get_surface()[0]
        Type = get_surface()[1]
        username = session['username']
        #  Gats the name of the correct surface and type
        surface_n_type = do_sql("""SELECT Coefficient.name, Site_type.name FROM
                                Coefficient,Site_type WHERE
                                Coefficient.type=Site_type.id and
                                Coefficient.id='{}'""".format(int(Type)), None)
        files = do_sql('''SELECT File_data.name, File_data.path FROM File_data,
                       User WHERE File_data.file_type=1 and
                       File_data.user_id=User.id and
                       User.username="{}";'''.format(username), None)
        try:
            Area = float(request.form['area'])
        except:
            # if area is broken then return error
            return render_template('Multi_Event.html', error=True,
                                   error_message='Invalid data',
                                   roof_type=roof_type,
                                   files=files,
                                   road_type=road_type,
                                   carpark_type=carpark_type,
                                   login_text=get_login_text())
        if Area <= 0:
            return render_template('Multi_Event.html', error=True,
                                   error_message="Area can't be < or = 0",
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
                                    str(randrange(9999999999)) +
                                    username + filename)
            csv.save(filepath)

            if not check_file_name(file_name):
                # error if file name exists under the current user
                return render_template('Multi_Event.html', error=True,
                                       error_message='File name already used',
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
            file = filedir + request.form['location']

        # file would only be none if it isn't valid
        if file is not None:
            try:
                data = csv_to_data(file, Area, Type, surface)
                # data based on user input
                input_data = [surface_n_type[0][1], Area, surface_n_type[0][0]]
                graph_data = data[0]
                data_to_csv("static/output/", username, data[1])
                output_data = "/static/output/" + username + ".csv"
                return render_template('Multi_Event.html', roof_type=roof_type,
                                       road_type=road_type,
                                       carpark_type=carpark_type,
                                       input_data=input_data, graph=graph,
                                       output_file=output_data, files=files,
                                       graph_data=json.dumps(graph_data),
                                       login_text=get_login_text())
            except:
                # returns error if anything breaks
                return render_template('Multi_Event.html', error=True,
                                       error_message='File Error',
                                       roof_type=roof_type, files=files,
                                       road_type=road_type,
                                       carpark_type=carpark_type,
                                       login_text=get_login_text())
        else:
            #  Throws an error if there is a problem with the file
            return render_template('Multi_Event.html', error=True,
                                   error_message='File Error',
                                   roof_type=roof_type, files=files,
                                   road_type=road_type,
                                   carpark_type=carpark_type,
                                   login_text=get_login_text())
    else:
        return render_template('needToLogin.html', login_text=get_login_text())


@app.route('/Login')
def Login():
    return render_template('Login.html', login_text=get_login_text())


@app.route('/Login', methods=['POST'])
def Login_Post():
    username = request.form['username']
    # encrypted and hashed password
    password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
    users = do_sql('SELECT * FROM User', None)
    for user in users:
        if str(username) == str(user[1]) and str(password) == str(user[2]):
            # sets session to username if correct user input and redirects
            session['username'] = username
            return redirect(url_for('Home_Page'))
    return render_template('Login.html', error=True, login_text=get_login_text())


@app.route('/SignUp')
def Sign_Up():
    return render_template('SignUp.html', error=False, login_text=get_login_text())


@app.route('/SignUp', methods=['POST'])
def Sign_Up_Post():
    # get user inputs
    username = request.form['username']
    password = request.form['password']
    redoPassword = request.form['redoPassword']
    email = request.form['email']

    unavalableUsernames = do_sql('SELECT username FROM User;', None)

    # username length constraint is 6
    if len(username) < 6:
        print("username too short")
        return render_template('SignUp.html', error=True, username_error=True,
                               error_message="Username has to be at least 6 characters",
                               login_text=get_login_text())

    # if username is taken then throw error
    for name in unavalableUsernames:
        if username == name[0]:
            print("unavalable username")
            return render_template('SignUp.html', error=True,
                                   username_error=True,
                                   error_message="Username already exists",
                                   login_text=get_login_text())

    # if email isnt a valid emain then throw error
    if not check_email(email):
        print("Invalid email address")
        return render_template('SignUp.html', error=True, email_error=True,
                               error_message="Invalid email address",
                               login_text=get_login_text())

    # if password is too short then throw error
    if len(password) < 8:
        print('password too short')
        return render_template('SignUp.html', error=True, password_error=True,
                               error_message="Password is less than 8 characters",
                               login_text=get_login_text())

    # if passwords do not match then throw error
    if redoPassword != password:
        print("non matching passwords")
        return render_template('SignUp.html', error=True, password_error=True,
                               error_message="Passwords do not match",
                               login_text=get_login_text())

    # if it gets past all of the constraints then insert the data
    # insert the hashed and encrypted version of the password
    do_sql('INSERT INTO User (username,password,email) VALUES (?,?,?);',
           (username, hashlib.sha256(password.encode('utf-8')).hexdigest(), email))

    # log in the user and redirect to home
    session['username'] = username
    return redirect(url_for('Home_Page'))


@app.route('/Privacy_Policy')
def PrivacyPolicy():
    return render_template('Privacy_policy.html', login_text=get_login_text())


@app.errorhandler(404)  # 404 page
def Page_Not_Found(error):
    return render_template('404page.html', login_text=get_login_text())


@app.errorhandler(500)
def Server_error(error):
    return render_template('500 page', login_text=get_login_text())


if __name__ == "__main__":  # Last lines
    app.run(debug=True)
