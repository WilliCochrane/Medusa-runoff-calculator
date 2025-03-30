from flask import Flask
import os

filedir =  os.path.abspath(os.path.dirname(__file__))
static_dir= os.path.join(filedir, 'static')
app = Flask(__name__, static_dir)

from app import routes

app.run(debug=True, port=4242)