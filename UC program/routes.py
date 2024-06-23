from flask import Flask, request, render_template
from math import exp, log, log10, floor
import sqlite3
import csv
import json

app = Flask(__name__)


def do_sql(sql):
    conn = sqlite3.connect('Coefficients.db')
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()


def rounded(num, sf):
    return round(num,sf-int(floor(log10(abs(num))))-1)

def calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface):
    coeff = do_sql("SELECT * FROM Coefficient WHERE id='{}'".format(int(Type)))
    sigfig = 5
    
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

    # Total Cu Coefficients
    b1 = coeff[0][13]
    b2 = coeff[0][14]
    b3 = coeff[0][15]
    b4 = coeff[0][16]
    b5 = coeff[0][17]
    b6 = coeff[0][18]
    b7 = coeff[0][19]
    b8 = coeff[0][20]
    g1 = coeff[0][22]

    # Total Zn Coefficients
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
        K = (-log(Cu0/Cuest))/(INT*Z)
        if DUR < Z:
            TCu = Cu0*Area*(1/K)*(1-exp(-K*INT*DUR))
        elif DUR >= Z:
            TCu = Cuest*Area*INT*(DUR - Z)+Cu0*Area*(1/K)*(1-exp(-K*INT*Z))

        # Calculating TZn roof
        Zn0 = (c1*PH+c2)*(c3*ADD**c4)*(c5*INT**c6)
        Znest = c7*PH+c8
        K = (-log(Znest/Zn0))/(INT*Z)
        if DUR <= Z:
            TZn = Zn0*Area*(1/K)*(1-exp(K*INT*DUR))
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

        TSS *= 1000
    TSS = rounded(TSS, sigfig)
    TCu = rounded(TCu, sigfig)
    TZn = rounded(TZn, sigfig)
    DCu = rounded(DCu, sigfig)
    DZn = rounded(DZn, sigfig)
    return [TSS, TCu, DCu, TZn, DZn]


def csv_to_data(fileDir, Area, Type, surface):
    with open(fileDir,newline='') as csvfile:
        graphData = []
        fileReader = csv.reader(csvfile)
        for row in fileReader:
            if row[0].isnumeric():
                graphData.append([int(row[0]),calculateRunoff(Area,float(row[2]),float(row[3]),float(row[4]),float(row[1]),Type,surface)[0]])
    return graphData


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
    return [surface,Type]
            

@app.route('/')
def form():
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1")
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2")
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3")
    return render_template('index.html', roof_type=roof_type, road_type=road_type, carpark_type=carpark_type)


@app.route('/', methods=['POST'])
def form_post():
    roof_type = do_sql("SELECT * FROM Coefficient WHERE type=1")
    road_type = do_sql("SELECT * FROM Coefficient WHERE type=2")
    carpark_type = do_sql("SELECT * FROM Coefficient WHERE type=3")

    graph = False
    single = False
    data = []
    surface = get_surface()[0]
    Type = get_surface()[1]
    # Single event simulation
    if int(request.form['event']) == 2:
        Area = float(request.form['area'])
        ADD = float(request.form['ADD'])
        INT = float(request.form['INT'])
        DUR = float(request.form['DUR'])
        PH = float(request.form['PH'])
        single = True
        data = calculateRunoff(Area, ADD, INT, DUR, PH, Type, surface)
        return render_template('index.html',roof_type=roof_type, road_type=road_type, carpark_type=carpark_type, TSS=data[0], TCu=data[1], DCu=data[2], TZn=data[3], DZn=data[4], single=single, graph=graph)
    # Full year simulation
    elif int(request.form['event']) == 1:
        Area = float(request.form['area'])
        graph = True
        surface = get_surface()[0]
        Type = get_surface()[1]
        if request.form.get('file_') == 'on':
            print(request.form.get('csv_input'))
        else:
            pass
        graph_data = csv_to_data("static\climate_data\climate_events_2011_CCC.csv", Area, Type, surface)
        return render_template('index.html', roof_type=roof_type, road_type=road_type, carpark_type=carpark_type, graph=graph, single=single, graph_data=json.dumps(graph_data))


if __name__ == "__main__":  # Last lines
    app.run(debug=True)
