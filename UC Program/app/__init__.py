from flask import Flask
import os

filedir =  os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=filedir+"static")

from app import routes

app.run(debug=True, port=4242)