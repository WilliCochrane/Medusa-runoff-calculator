from flask import Flask, request, render_template
from math import exp, log, e
import sqlite3

app = Flask(__name__)


def do_sql(sql):
    conn = sqlite3.connect('Coefficients.db')
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()


def rounded(num, sf):
    return round(num*(10**sf))/(10**sf)

@app.route('/')
def form():
    roof_type = do_sql("SELECT * FROM Info WHERE type=1")
    road_type = do_sql("SELECT * FROM Info WHERE type=2")
    return render_template('index.html', roof_type=roof_type, road_type=road_type)


@app.route('/', methods=['POST'])
def form_post():
    roof_type = do_sql("SELECT * FROM Info WHERE type=1")
    road_type = do_sql("SELECT * FROM Info WHERE type=2")

    graph = False
    roof_data = False

    if request.form['area'] and request.form['type'] != "no" and request.form['event'] == "2":
        if request.form['ADD'] and request.form['INT'] and request.form['DUR'] and request.form['PH']:
            coeff = do_sql("SELECT * FROM Info WHERE id='{}'".format(int(request.form['type'])))

            Area = float(request.form['area'])
            ADD = float(request.form['ADD'])
            INT = float(request.form['INT'])
            DUR = float(request.form['DUR'])
            PH = float(request.form['PH'])

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
            TSS = rounded(TSS, 4)

            # Calculating TCu roof
            Cu0 = (b1*PH**b2)*(b3*ADD**b4)*(b5*INT**b6)
            Cuest = b7*PH**b8
            K = (-log(Cu0/Cuest))/(INT*Z)
            print(K)
            if DUR < Z:
                TCu = Cu0*Area*(1/K)*(1-exp(-K*INT*DUR))
            elif DUR >= Z:
                TCu = Cuest*Area*INT*(DUR - Z)+Cu0*Area*(1/K)*(1-exp(-K*INT*Z))
            TCu = rounded(TCu, 4)

            # Calculating TZn roof
            Zn0 = (c1*PH+c2)*(c3*ADD**c4)*(c5*INT**c6)
            print(Cu0)
            Znest = c7*PH+c8
            print(Cuest)
            K = (-log(Znest/Zn0))/(INT*Z)
            if DUR <= Z:
                TZn = Zn0*Area*(1/K)*(1-exp(K*INT*DUR))
            elif DUR > Z:
                TZn = Znest*Area*INT*(DUR-Z)+Zn0*Area*1/1000/K*(1-exp(-K*INT*Z))
                print(TCu)
            TZn = rounded(TZn, 4)

            # Calculating DCu roof
            DCu = l1*TCu
            DCu = rounded(DCu, 4)

            # Calculating DZn roof
            DZn = m1*TZn
            DZn = rounded(DZn, 4)

            roof_data = True
        elif request.form['area'] and request.form['event'] == "2" and request.form['type'] != "no":
            graph = True
    
    return render_template('index.html',roof_type=roof_type, road_type=road_type, roof_TSS=TSS, roof_TCu=TCu, roof_DCu=DCu, roof_TZn=TZn, roof_DZn=DZn, roof_data=roof_data, graph=graph)


if __name__ == "__main__":  # Last lines
    app.run(debug=True)
