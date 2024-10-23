from flask import render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from backend import app
from backend.app import GestorDatos

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cargar', methods=['GET', 'POST'])
def cargar_archivo():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Procesar el archivo con GestorDatos
            gestor = GestorDatos()
            gestor.agregar_mensajes(filepath)
            gestor.agregar_palabras(filepath)
            gestor.agregar_empresas(filepath)
            gestor.generar_xml_salida(filepath)
            
            flash('Archivo cargado y procesado exitosamente')
            return redirect(url_for('lista_archivos'))
    return render_template('cargar_archivo.html')

@app.route('/archivos')
def lista_archivos():
    archivos = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('lista_archivos.html', archivos=archivos)