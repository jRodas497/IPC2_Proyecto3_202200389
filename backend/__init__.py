import os
from flask import Flask

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'backend/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xml'}

app.template_folder = '../frontend/templates'
app.static_folder = '../frontend/static'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
