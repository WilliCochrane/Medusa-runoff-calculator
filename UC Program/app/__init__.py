from flask import Flask
import os

filedir =  os.path.dirname(os.path.abspath(__file__))
static_dir= os.path.join(filedir, 'static')
app = Flask(__name__)

from app import routes
if __name__ == '__main__':
    app.run(debug=True, port=4242)