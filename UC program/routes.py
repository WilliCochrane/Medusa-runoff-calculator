from flask import Flask, request, render_template, session, redirect, url_for, jsonify, json, current_app
from werkzeug.utils import secure_filename
from math import exp, log, log10, floor, sqrt
from random import randrange
import hashlib
import sqlite3
import zipfile
import stripe
import json
import xlwt
import csv
import os

# This is your test secret API key.
stripe.api_key = 'sk_test_51QEKXbASoVcyVGhrVn85dRlBcFTOLwkFjXrce6BCyzYIhQoN92EUNCPgkmXcMfl3JGDgK9OhjUeBnZqjg1jXS6cO00gpwYzXCf'


# This bellow is just for ease of use with pythonanywhere
# filedir = "/home/willicochrane/"
filedir = ""
domain = 'http://localhost:4242'

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
def calculateRunoff(Area : float, ADD : float, INT : float, DUR : float, PH : float, Type : int) -> list:
    coeff = do_sql("SELECT * FROM Coefficient WHERE id='{}'".format(Type), None)
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
            if row[0].isalpha() or row[1].isalpha() or int(row[0]) > num_of_surfaces:
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
    zipFilepath = username +".zip"

    make_filepath_avalable("static/output/"+zipFilepath)

    wb.save(filepath)
    zip = zipfile.ZipFile(zipFilepath, "w", zipfile.ZIP_DEFLATED)
    zip.write(filepath)
    zip.close()
    os.rename(zipFilepath, "static/output/"+zipFilepath)
    os.remove(filepath)


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


# multi_surface_to_xlsl("static\climate_data\climate_events_2011_CCC.csv","static\climate_data\climate_events_2011_CCC.csv", "xlslfile")


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
        graph = True
        file = None

        if request.form.get('Surface_file_') == 'on':
            surface_csv = request.files['surface_csv']
            filename = secure_filename(surface_csv)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'surface_file_' + username)
            make_filepath_avalable(filepath)
            surface_csv.save(filepath)

        surface = get_surface()[0]
        Type = get_surface()[1]  # Type spesific type of the surface input
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
                                   error_message="Area can't be less than or equal to  0",
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
            file = request.form['location']

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
                                       road_type=road_type, single_surface=True,
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


@app.route('/Checkout')
def Checkout():
    return render_template('checkout.html')


@app.route('/Sucess')
def Success():
    return render_template('success.html')


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
            '/Sucess?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain + '/cancel.html',
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


@app.route('/webhook', methods=['POST'])
def webhook_received():
    # Replace this endpoint secret with your endpoint's unique secret
    # If you are testing with the CLI, find the secret by running 'stripe listen'
    # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
    # at https://dashboard.stripe.com/webhooks
    webhook_secret = 'whsec_huw*(F1)#!D!JD(hud9G!'
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']

    print('event ' + event_type)

    if event_type == 'checkout.session.completed':
        print('🔔 Payment succeeded!')
    elif event_type == 'customer.subscription.trial_will_end':
        print('Subscription trial will end')
    elif event_type == 'customer.subscription.created':
        print('Subscription created %s', event.id)
    elif event_type == 'customer.subscription.updated':
        print('Subscription created %s', event.id)
    elif event_type == 'customer.subscription.deleted':
        # handle subscription canceled automatically based
        # upon your subscription settings. Or if the user cancels it.
        print('Subscription canceled: %s', event.id)
    elif event_type == 'entitlements.active_entitlement_summary.updated':
        # handle active entitlement summary updated
        print('Active entitlement summary updated: %s', event.id)

    return jsonify({'status': 'success'})


@app.errorhandler(404)  # 404 page
def Page_Not_Found(error):
    return render_template('404page.html', login_text=get_login_text())


@app.errorhandler(500)
def Server_error(error):
    return render_template('500 page', login_text=get_login_text())


if __name__ == "__main__":  # Last lines
    app.run(debug=True, port=4242)
