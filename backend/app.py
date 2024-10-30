#----------------- IMPORTACIONES -------------------
from flask import Flask, flash, request, redirect, send_file, url_for, render_template, session, jsonify
from werkzeug.utils import secure_filename
from fpdf import FPDF
from tkinter import filedialog
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom.minidom import Document
from django.shortcuts import render, redirect
from rest_framework.response import Response
import os
import string
import re
import unicodedata
from reportlab.pdfgen import canvas
import io
from reportlab.lib.pagesizes import letter
import base64
from io import BytesIO
#---------------- GESTOR DE DATOS ------------------  

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'
app.config['ALLOWED_EXTENSIONS'] = {'xml'}

app.template_folder = '../frontend/app/templates'
app.static_folder = '../frontend/app/static'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    return texto

class Nodo:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None

class ListaEnlazada:
    def __init__(self):
        self.cabeza = None

    def agregar(self, valor):
        nuevo_nodo = Nodo(valor)
        if not self.cabeza:
            self.cabeza = nuevo_nodo
        else:
            actual = self.cabeza
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo

    def iterar(self):
        actual = self.cabeza
        while actual:
            yield actual.valor
            actual = actual.siguiente
            
    def contiene(self, valor, key = lambda x:x):
        actual = self.cabeza
        while actual:
            if key(actual.valor) == key(valor):
                return True
            actual = actual.siguiente
        return False

class Mensaje:
    def __init__(self, lugar, fecha, hora, usuario, red_social, contenido):
        self.lugar = lugar
        self.fecha = fecha
        self.hora = hora
        self.usuario = usuario
        self.red_social = red_social
        self.contenido = contenido
        self.positivas = 0
        self.negativas = 0
        self.clasificacion = 'neutro'

    @staticmethod
    def parsear_mensaje(texto):
        texto = " ".join(texto.split())
        
        lugar_fecha_patron = r"Lugar y fecha: ([^,]+), ([^\\n]+)"
        usuario_patron = r"Usuario: ([^\s]+)"
        red_social_patron = r"Red social: ([^\s]+)"
        contenido_patron = r"Red social: [^\s]+\s+(.*)"

        lugar_fecha = re.search(lugar_fecha_patron, texto)
        usuario = re.search(usuario_patron, texto)
        red_social = re.search(red_social_patron, texto)
        contenido = re.search(contenido_patron, texto, re.DOTALL)

        if lugar_fecha and usuario and red_social and contenido:
            lugar = lugar_fecha.group(1)
            fecha_hora = lugar_fecha.group(2)
            usuario = usuario.group(1)
            red_social = red_social.group(1)
            contenido = contenido.group(1).strip()
            
            fecha_patron = r"\d{2}/\d{2}/\d{4}"
            hora_patron = r"\d{2}:\d{2}"
            fecha_hora_patron = rf"({fecha_patron})\s+({hora_patron})"
            fecha_hora_match = re.search(fecha_hora_patron, fecha_hora)
            
            #print(f'Lugar: {lugar} | Fecha: {fecha} | Usuario: {usuario} | Red social: {red_social} | Contenido: {contenido}')
            if fecha_hora_match:
                fecha = fecha_hora_match.group(1)
                hora = fecha_hora_match.group(2)
                return Mensaje(lugar, fecha, hora, usuario, red_social, contenido)
            else:
                raise ValueError("Formato de fecha u hora incorrecto")
        else:
            raise ValueError("Formato de mensaje incorrecto")

    def analizar_sentimientos(self, palabras_positivas, palabras_negativas):
        if self.positivas != 0 or self.negativas != 0:
            return
        
        tabla_traduccion = str.maketrans('', '', string.punctuation)
        
        contenido_normalizado = normalizar_texto(self.contenido).translate(tabla_traduccion)
        palabras = contenido_normalizado.split()
        
        for palabra in palabras:
            if palabras_positivas.contiene(Palabra(palabra, 'positivo'), key=lambda x: x.texto):
                self.positivas += 1
            if palabras_negativas.contiene(Palabra(palabra, 'negativo'), key=lambda x: x.texto):
                self.negativas += 1

        if self.positivas > self.negativas:
            self.clasificacion = "positivo"
        elif self.negativas > self.positivas:
            self.clasificacion = "negativo"
        else:
            self.clasificacion = "neutro"   

    def to_dict(self):
        return {
            "fecha": self.fecha,
            "usuario": self.usuario,
            "contenido": self.contenido,
            "clasificacion": self.clasificacion
        }

class Palabra:
    def __init__(self, texto, tipo):
        self.texto = texto
        self.tipo = tipo
        
    def __str__(self):
        return self.texto

class Servicio:
    def __init__(self, nombre):
        self.nombre = nombre
        self.aliases = ListaEnlazada()
        self.total_mensajes = 0
        self.mensajes_positivos = 0
        self.mensajes_negativos = 0
        self.mensajes_neutros = 0
        
    def __str__(self):
        return self.nombre

    def agregar_alias(self, alias):
        if not self.aliases.contiene(alias):
            self.aliases.agregar(alias)
        else:
            print(f"Alias repetido: {alias}")

    def incrementar_conteo(self, clasificacion):
        self.total_mensajes += 1
        if clasificacion == "positivo":
            self.mensajes_positivos += 1
        elif clasificacion == "negativo":
            self.mensajes_negativos += 1
        elif clasificacion == "neutro":
            self.mensajes_neutros += 1
            
    def se_menciona(self, contenido):
        contenido_normalizado = normalizar_texto(contenido)
        if self.nombre in contenido_normalizado:
            return True
        for alias in self.aliases.iterar():
            if alias in contenido_normalizado:
                return True
        return False

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "aliases": self.aliases
        }

class Empresa:
    def __init__(self, nombre):
        self.nombre = nombre
        self.servicios = ListaEnlazada()
        self.total_mensajes = 0
        self.mensajes_positivos = 0
        self.mensajes_negativos = 0
        self.mensajes_neutros = 0

    def agregar_servicio(self, servicio):
        if not self.servicios.contiene(servicio, key=lambda x: x.nombre):
            self.servicios.agregar(servicio)
        else:
            print(f"El servicio {servicio.nombre} ya existe en la empresa {self.nombre}")

    def incrementar_conteo(self, clasificacion):
        self.total_mensajes += 1
        if clasificacion == "positivo":
            self.mensajes_positivos += 1
        elif clasificacion == "negativo":
            self.mensajes_negativos += 1
        elif clasificacion == "neutro":
            self.mensajes_neutros += 1
            
    def to_dict(self):
        return {
            "nombre": self.nombre,
            "servicios": [servicio.to_dict() for servicio in self.servicios]
        }

class FechaMensajes:
    def __init__(self, fecha):
        self.fecha = fecha
        self.mensajes = ListaEnlazada()
        self.siguiente = None

    def agregar_mensaje(self, mensaje):
        self.mensajes.agregar(mensaje)

class MensajesPorFecha:
    def __init__(self):
        self.fechas = ListaEnlazada()

    def agregar_mensaje(self, fecha, mensaje):
        actual_fecha = self.fechas.cabeza
        while actual_fecha:
            if actual_fecha.valor.fecha == fecha:
                actual_fecha.valor.agregar_mensaje(mensaje)
                return
            actual_fecha = actual_fecha.siguiente
        nueva_fecha = FechaMensajes(fecha)
        nueva_fecha.agregar_mensaje(mensaje)
        self.fechas.agregar(nueva_fecha)

    def iterar(self):
        return self.fechas.iterar()

class GestorDatos:
    def __init__(self):
        self.mensajes = ListaEnlazada()
        self.palabras_positivas = ListaEnlazada()
        self.palabras_negativas = ListaEnlazada()
        self.empresas = ListaEnlazada()
        self.mensajes_por_fecha = MensajesPorFecha()

    def limpiar_datos(self):
        self.mensajes = ListaEnlazada()
        self.palabras_positivas = ListaEnlazada()
        self.palabras_negativas = ListaEnlazada()
        self.empresas = ListaEnlazada()
        self.mensajes_por_fecha = MensajesPorFecha()
    
    def agregar_mensajes(self, contenido_archivo):
        nuevos_mensajes = leer_mensajes(contenido_archivo)
        for mensaje in nuevos_mensajes.iterar():
            self.mensajes.agregar(mensaje)

    def agregar_palabras(self, contenido_archivo):
        nuevas_palabras = leer_diccionario(contenido_archivo)
        for palabra in nuevas_palabras.iterar():
            if palabra.tipo == 'positivo':
                if not self.palabras_positivas.contiene(palabra, key=lambda x: x.texto) and not self.palabras_negativas.contiene(palabra, key=lambda x: x.texto):
                    self.palabras_positivas.agregar(palabra)
                else:
                    print(f"Palabra repetida o en conflicto: {palabra.texto}")
            elif palabra.tipo == 'negativo':
                if not self.palabras_negativas.contiene(palabra, key=lambda x: x.texto) and not self.palabras_positivas.contiene(palabra, key=lambda x: x.texto):
                    self.palabras_negativas.agregar(palabra)
                else:
                    print(f"Palabra repetida o en conflicto: {palabra.texto}")
       
        print('-' * 50)
            
    def agregar_empresas(self, contenido_archivo):
        nuevas_empresas = leer_empresas(contenido_archivo)
        for empresa in nuevas_empresas.iterar():
            if not self.empresas.contiene(empresa, key=lambda x: x.nombre):
                self.empresas.agregar(empresa)
            else:
                print(f"Empresa repetida: {empresa.nombre}")
                
        print('-' * 50)

    def contar_mensajes_por_empresa(self):
        for texto in self.mensajes.iterar():
            mensaje = Mensaje.parsear_mensaje(texto)
            mensaje.analizar_sentimientos(self.palabras_positivas, self.palabras_negativas)
            empresas_mencionadas = set()
            for empresa in self.empresas.iterar():
                if empresa.nombre in normalizar_texto(mensaje.contenido) and empresa.nombre not in empresas_mencionadas:
                    empresa.incrementar_conteo(mensaje.clasificacion)
                    empresas_mencionadas.add(empresa.nombre)
                for servicio in empresa.servicios.iterar():
                    if servicio.se_menciona(mensaje.contenido) and servicio.nombre not in empresas_mencionadas:
                        servicio.incrementar_conteo(mensaje.clasificacion)
                        empresas_mencionadas.add(servicio.nombre)

    def mostrar_mensajes(self):
        print("Mensajes agrupados por fecha:")
        for texto in self.mensajes.iterar():
            mensaje = Mensaje.parsear_mensaje(texto)
            self.mensajes_por_fecha.agregar_mensaje(mensaje.fecha, mensaje)

        actual_fecha = self.mensajes_por_fecha.fechas.cabeza
        while actual_fecha:
            print("*****" * 5 )
            print(f"Fecha: {actual_fecha.valor.fecha}")
            print("*****" * 5 )
            actual_mensaje = actual_fecha.valor.mensajes.cabeza
            while actual_mensaje:
                mensaje = actual_mensaje.valor
                mensaje.analizar_sentimientos(self.palabras_positivas, self.palabras_negativas)
                print(f"  Lugar: {mensaje.lugar}")
                print(f"  Hora: {mensaje.hora}")
                print(f"  Usuario: {mensaje.usuario}")
                print(f"  Red Social: {mensaje.red_social}")
                print(f"  Contenido: {mensaje.contenido}")
                print(f"  Palabras Positivas: {mensaje.positivas}")
                print(f"  Palabras Negativas: {mensaje.negativas}")
                print(f"  Clasificación: {mensaje.clasificacion}")
                print("  ------")
                actual_mensaje = actual_mensaje.siguiente
            actual_fecha = actual_fecha.siguiente

    def mostrar_palabras(self):
        print("\nPalabras del Diccionario:")
        print('     Positivas:')
        for palabra in self.palabras_positivas.iterar():
            print(f"        Palabra: {palabra.texto}")
        print('     Negativas:')
        for palabra in self.palabras_negativas.iterar():
            print(f"        Palabra: {palabra.texto}")
            
    def mostrar_empresas(self):
        print("\nEmpresas y Servicios:")
        for empresa in self.empresas.iterar():
            print(f"Empresa: {empresa.nombre}")
            for servicio in empresa.servicios.iterar():
                print(f"  Servicio: {servicio.nombre}")
                for alias in servicio.aliases.iterar():
                    print(f"    Alias: {alias}")

    def mostrar_resumen(self):
        self.contar_mensajes_por_empresa()
        print("\nResumen de Mensajes por Empresa y Servicio:")
        for empresa in self.empresas.iterar():
            print('-#' * 25)
            print(f"Empresa: {empresa.nombre}")
            print(f"  Total de Mensajes: {empresa.total_mensajes}")
            print(f"  Mensajes Positivos: {empresa.mensajes_positivos}")
            print(f"  Mensajes Negativos: {empresa.mensajes_negativos}")
            print(f"  Mensajes Neutros: {empresa.mensajes_neutros}")
            for servicio in empresa.servicios.iterar():
                print("  ------------------------------------")
                print(f"  Servicio: {servicio.nombre}")
                print(f"    Total de Mensajes: {servicio.total_mensajes}")
                print(f"    Mensajes Positivos: {servicio.mensajes_positivos}")
                print(f"    Mensajes Negativos: {servicio.mensajes_negativos}")
                print(f"    Mensajes Neutros: {servicio.mensajes_neutros}")
            print("\n")
      
    def mostrar_resumen_detallado(self):
        self.contar_mensajes_por_empresa()
        actual_fecha = self.mensajes_por_fecha.fechas.cabeza
        while actual_fecha:
            print(f"FECHA: {actual_fecha.valor.fecha}")
            total_mensajes = 0
            positivos = 0
            negativos = 0
            neutros = 0
            actual_mensaje = actual_fecha.valor.mensajes.cabeza
            while actual_mensaje:
                mensaje = actual_mensaje.valor
                total_mensajes += 1
                if mensaje.clasificacion == "positivo":
                    positivos += 1
                elif mensaje.clasificacion == "negativo":
                    negativos += 1
                else:
                    neutros += 1
                actual_mensaje = actual_mensaje.siguiente

            print(f"Cantidad total de mensajes recibidos: {total_mensajes}")
            print(f"Cantidad total de mensajes positivos: {positivos}")
            print(f"Cantidad total de mensajes negativos: {negativos}")
            print(f"Cantidad total de mensajes neutros: {neutros}")

            for empresa in self.empresas.iterar():
                total_empresa_mensajes = 0
                total_empresa_positivos = 0
                total_empresa_negativos = 0
                total_empresa_neutros = 0
                actual_mensaje = actual_fecha.valor.mensajes.cabeza
                while actual_mensaje:
                    mensaje = actual_mensaje.valor
                    if empresa.nombre in normalizar_texto(mensaje.contenido):
                        total_empresa_mensajes += 1
                        if mensaje.clasificacion == "positivo":
                            total_empresa_positivos += 1
                        elif mensaje.clasificacion == "negativo":
                            total_empresa_negativos += 1
                        else:
                            total_empresa_neutros += 1
                    actual_mensaje = actual_mensaje.siguiente

                print(f"  Empresa: {empresa.nombre}")
                print(f"    Número total de mensajes que mencionan a Empresa: {total_empresa_mensajes}")
                print(f"    Mensajes positivos: {total_empresa_positivos}")
                print(f"    Mensajes negativos: {total_empresa_negativos}")
                print(f"    Mensajes neutros: {total_empresa_neutros}")

                for servicio in empresa.servicios.iterar():
                    total_servicio_mensajes = 0
                    total_servicio_positivos = 0
                    total_servicio_negativos = 0
                    total_servicio_neutros = 0
                    actual_mensaje = actual_fecha.valor.mensajes.cabeza
                    while actual_mensaje:
                        mensaje = actual_mensaje.valor
                        if servicio.se_menciona(mensaje.contenido):
                            total_servicio_mensajes += 1
                            if mensaje.clasificacion == "positivo":
                                total_servicio_positivos += 1
                            elif mensaje.clasificacion == "negativo":
                                total_servicio_negativos += 1
                            else:
                                total_servicio_neutros += 1
                        actual_mensaje = actual_mensaje.siguiente

                    print(f"    Servicio: {servicio.nombre}")
                    print(f"      Número total de mensajes que mencionan al servicio: {total_servicio_mensajes}")
                    print(f"      Mensajes positivos: {total_servicio_positivos}")
                    print(f"      Mensajes negativos: {total_servicio_negativos}")
                    print(f"      Mensajes neutros: {total_servicio_neutros}")

            actual_fecha = actual_fecha.siguiente

    def generar_xml_salida(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_uploads = os.path.join(directorio_actual, 'uploads')
        
        if not os.path.exists(ruta_uploads):
            os.makedirs(ruta_uploads)
        
        archivo_salida = os.path.join(ruta_uploads, "archivo_salida.xml")
        
        doc = Document()
        root = doc.createElement("lista_respuestas")
        doc.appendChild(root)
        actual_fecha = self.mensajes_por_fecha.fechas.cabeza
        while actual_fecha:
            respuesta = doc.createElement("respuesta")
            root.appendChild(respuesta)
            fecha = doc.createElement("fecha")
            fecha.appendChild(doc.createTextNode(actual_fecha.valor.fecha))
            respuesta.appendChild(fecha)
            mensajes = doc.createElement("mensajes")
            respuesta.appendChild(mensajes)
            total_mensajes = 0
            positivos = 0
            negativos = 0
            neutros = 0
            actual_mensaje = actual_fecha.valor.mensajes.cabeza
            while actual_mensaje:
                mensaje = actual_mensaje.valor
                total_mensajes += 1
                if mensaje.clasificacion == "positivo":
                    positivos += 1
                elif mensaje.clasificacion == "negativo":
                    negativos += 1
                else:
                    neutros += 1
                actual_mensaje = actual_mensaje.siguiente

            total_elem = doc.createElement("total")
            total_elem.appendChild(doc.createTextNode(str(total_mensajes)))
            mensajes.appendChild(total_elem)

            positivos_elem = doc.createElement("positivos")
            positivos_elem.appendChild(doc.createTextNode(str(positivos)))
            mensajes.appendChild(positivos_elem)

            negativos_elem = doc.createElement("negativos")
            negativos_elem.appendChild(doc.createTextNode(str(negativos)))
            mensajes.appendChild(negativos_elem)

            neutros_elem = doc.createElement("neutros")
            neutros_elem.appendChild(doc.createTextNode(str(neutros)))
            mensajes.appendChild(neutros_elem)

            analisis = doc.createElement("analisis")
            respuesta.appendChild(analisis)

            for empresa in self.empresas.iterar():
                empresa_elem = doc.createElement("empresa")
                empresa_elem.setAttribute("nombre", empresa.nombre)
                analisis.appendChild(empresa_elem)

                mensajes_empresa = doc.createElement("mensajes")
                empresa_elem.appendChild(mensajes_empresa)

                total_empresa = 0
                positivos_empresa = 0
                negativos_empresa = 0
                neutros_empresa = 0

                for servicio in empresa.servicios.iterar():
                    total_empresa += servicio.total_mensajes
                    positivos_empresa += servicio.mensajes_positivos
                    negativos_empresa += servicio.mensajes_negativos
                    neutros_empresa += servicio.mensajes_neutros

                total_empresa_elem = doc.createElement("total")
                total_empresa_elem.appendChild(doc.createTextNode(str(total_empresa)))
                mensajes_empresa.appendChild(total_empresa_elem)

                positivos_empresa_elem = doc.createElement("positivos")
                positivos_empresa_elem.appendChild(doc.createTextNode(str(positivos_empresa)))
                mensajes_empresa.appendChild(positivos_empresa_elem)

                negativos_empresa_elem = doc.createElement("negativos")
                negativos_empresa_elem.appendChild(doc.createTextNode(str(negativos_empresa)))
                mensajes_empresa.appendChild(negativos_empresa_elem)

                neutros_empresa_elem = doc.createElement("neutros")
                neutros_empresa_elem.appendChild(doc.createTextNode(str(neutros_empresa)))
                mensajes_empresa.appendChild(neutros_empresa_elem)

                servicios_elem = doc.createElement("servicios")
                empresa_elem.appendChild(servicios_elem)

                for servicio in empresa.servicios.iterar():
                    servicio_elem = doc.createElement("servicio")
                    servicio_elem.setAttribute("nombre", servicio.nombre)
                    servicios_elem.appendChild(servicio_elem)

                    mensajes_servicio = doc.createElement("mensajes")
                    servicio_elem.appendChild(mensajes_servicio)

                    total_servicio_elem = doc.createElement("total")
                    total_servicio_elem.appendChild(doc.createTextNode(str(servicio.total_mensajes)))
                    mensajes_servicio.appendChild(total_servicio_elem)

                    positivos_servicio_elem = doc.createElement("positivos")
                    positivos_servicio_elem.appendChild(doc.createTextNode(str(servicio.mensajes_positivos)))
                    mensajes_servicio.appendChild(positivos_servicio_elem)

                    negativos_servicio_elem = doc.createElement("negativos")
                    negativos_servicio_elem.appendChild(doc.createTextNode(str(servicio.mensajes_negativos)))
                    mensajes_servicio.appendChild(negativos_servicio_elem)

                    neutros_servicio_elem = doc.createElement("neutros")
                    neutros_servicio_elem.appendChild(doc.createTextNode(str(servicio.mensajes_neutros)))
                    mensajes_servicio.appendChild(neutros_servicio_elem)

            actual_fecha = actual_fecha.siguiente

        with open(os.path.join('uploads', 'archivo_salida.xml'), "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent="  "))
        print(f"Archivo XML guardado exitosamente en {archivo_salida}")

    def prueba_de_mensaje(self, contenido_archivo):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_uploads = os.path.join(directorio_actual, 'uploads')
        
        if not os.path.exists(ruta_uploads):
            os.makedirs(ruta_uploads)
        
        archivo_salida = os.path.join(ruta_uploads, "msjPRUEBA.xml")
        
        root = ET.fromstring(contenido_archivo)

        if root.tag != 'mensaje' or len(root) != 0:
            print("El archivo XML no contiene únicamente la etiqueta <mensaje>")
            return

        mensaje_texto = root.text.strip()

        mensaje = Mensaje.parsear_mensaje(mensaje_texto)
        mensaje.analizar_sentimientos(self.palabras_positivas, self.palabras_negativas)

        doc = Document()
        respuesta = doc.createElement("respuesta")
        doc.appendChild(respuesta)

        fecha = doc.createElement("fecha")
        fecha.appendChild(doc.createTextNode(mensaje.fecha))
        respuesta.appendChild(fecha)

        red_social = doc.createElement("red_social")
        red_social.appendChild(doc.createTextNode(mensaje.red_social))
        respuesta.appendChild(red_social)

        usuario = doc.createElement("usuario")
        usuario.appendChild(doc.createTextNode(mensaje.usuario))
        respuesta.appendChild(usuario)

        empresas_elem = doc.createElement("empresas")
        respuesta.appendChild(empresas_elem)

        empresas_mencionadas = set()
        for empresa in self.empresas.iterar():
            if empresa.nombre in normalizar_texto(mensaje.contenido):
                empresa_elem = doc.createElement("empresa")
                empresa_elem.setAttribute("nombre", empresa.nombre)
                empresas_elem.appendChild(empresa_elem)
                empresas_mencionadas.add(empresa.nombre)

                for servicio in empresa.servicios.iterar():
                    if servicio.se_menciona(mensaje.contenido):
                        servicio_elem = doc.createElement("servicio")
                        servicio_elem.appendChild(doc.createTextNode(servicio.nombre))
                        empresa_elem.appendChild(servicio_elem)

        palabras_positivas_elem = doc.createElement("palabras_positivas")
        palabras_positivas_elem.appendChild(doc.createTextNode(str(mensaje.positivas)))
        respuesta.appendChild(palabras_positivas_elem)

        palabras_negativas_elem = doc.createElement("palabras_negativas")
        palabras_negativas_elem.appendChild(doc.createTextNode(str(mensaje.negativas)))
        respuesta.appendChild(palabras_negativas_elem)

        total_palabras = mensaje.positivas + mensaje.negativas
        sentimiento_positivo = (mensaje.positivas / total_palabras) * 100 if total_palabras > 0 else 0
        sentimiento_negativo = (mensaje.negativas / total_palabras) * 100 if total_palabras > 0 else 0

        sentimiento_positivo_elem = doc.createElement("sentimiento_positivo")
        sentimiento_positivo_elem.appendChild(doc.createTextNode(f"{sentimiento_positivo:.2f}%"))
        respuesta.appendChild(sentimiento_positivo_elem)

        sentimiento_negativo_elem = doc.createElement("sentimiento_negativo")
        sentimiento_negativo_elem.appendChild(doc.createTextNode(f"{sentimiento_negativo:.2f}%"))
        respuesta.appendChild(sentimiento_negativo_elem)

        sentimiento_analizado_elem = doc.createElement("sentimiento_analizado")
        sentimiento_analizado_elem.appendChild(doc.createTextNode(mensaje.clasificacion))
        respuesta.appendChild(sentimiento_analizado_elem)

        with open(os.path.join('uploads', 'msjPRUEBA.xml'), "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent="  "))
        print(f"Archivo XML guardado exitosamente en {archivo_salida}")

    def filtrar_mensajes(self, fecha, empresa):
        mensajes_filtrados = ListaEnlazada()
        actual = self.mensajes.cabeza
        encontrado = False
        while actual:
            mensaje = actual.valor
            if isinstance(mensaje, Mensaje) and mensaje.fecha == fecha and empresa.lower() in mensaje.contenido.lower():
                encontrado = True
                print(f"Filtrado - Lugar: {mensaje.lugar}")
                print(f'Fecha: {mensaje.fecha} | Hora: {mensaje.hora} | Usuario: {mensaje.usuario}')
                print(f'Red Social: {mensaje.red_social} | Contenido: {mensaje.contenido}')
                mensajes_filtrados.agregar(mensaje)
            actual = actual.siguiente
        
        if not encontrado:
            print(f"No se encontraron mensajes para la fecha {fecha} y la empresa {empresa}.")
        
        #return mensajes_filtrados
        
    def generar_reporte_pdf(self):
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 12)
                self.cell(0, 10, 'Reporte de Mensajes por Empresa y Servicio', 0, 1, 'C')

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

        pdf = PDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)

        for empresa in self.empresas.iterar():
            pdf.cell(0, 10, f"Empresa: {empresa.nombre}", 0, 1)
            pdf.cell(10)
            pdf.cell(0, 10, f"Mensajes Totales: {empresa.mensajes_positivos + empresa.mensajes_negativos + empresa.mensajes_neutros}", 0, 1)
            pdf.cell(10)
            pdf.cell(0, 10, f"Mensajes Positivos: {empresa.mensajes_positivos}", 0, 1)
            pdf.cell(10)
            pdf.cell(0, 10, f"Mensajes Negativos: {empresa.mensajes_negativos}", 0, 1)
            pdf.cell(10)
            pdf.cell(0, 10, f"Mensajes Neutros: {empresa.mensajes_neutros}", 0, 1)
            pdf.cell(10)

            for servicio in empresa.servicios.iterar():
                pdf.cell(20)
                pdf.cell(0, 10, f"Servicio: {servicio.nombre}", 0, 1)
                pdf.cell(30)
                pdf.cell(0, 10, f"Mensajes Totales: {servicio.mensajes_positivos + servicio.mensajes_negativos + servicio.mensajes_neutros}", 0, 1)
                pdf.cell(30)
                pdf.cell(0, 10, f"Mensajes Positivos: {servicio.mensajes_positivos}", 0, 1)
                pdf.cell(30)
                pdf.cell(0, 10, f"Mensajes Negativos: {servicio.mensajes_negativos}", 0, 1)
                pdf.cell(30)
                pdf.cell(0, 10, f"Mensajes Neutros: {servicio.mensajes_neutros}", 0, 1)
                pdf.cell(10)

            pdf.cell(0, 10, '', 0, 1)  # Espacio entre empresas

        pdf.output('reporte.pdf')

    def mostrar_mensajes_por_rango(self, fecha_inicio, fecha_fin):
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%d/%m/%Y')
        fecha_fin_dt = datetime.strptime(fecha_fin, '%d/%m/%Y')

        for fecha_obj in self.mensajes_por_fecha.iterar():
            fecha_dt = datetime.strptime(fecha_obj.fecha, '%d/%m/%Y')
            if fecha_inicio_dt <= fecha_dt <= fecha_fin_dt:
                print(f"Fecha: {fecha_obj.fecha}")
                for mensaje in fecha_obj.mensajes.iterar():
                    print(f"  Lugar: {mensaje.lugar}")
                    print(f"  Hora: {mensaje.hora}")
                    print(f"  Usuario: {mensaje.usuario}")
                    print(f"  Red Social: {mensaje.red_social}")
                    print(f"  Contenido: {mensaje.contenido}")
                    print(f"  Clasificación: {mensaje.clasificacion}")
                    print("  ------")

    def formatear_datos(self):
        resumen = ''
        
        self.contar_mensajes_por_empresa()
        actual_fecha = self.mensajes_por_fecha.fechas.cabeza
        while actual_fecha:
            resumen += f"FECHA: {actual_fecha.valor.fecha}\n"
            total_mensajes = 0
            positivos = 0
            negativos = 0
            neutros = 0
            actual_mensaje = actual_fecha.valor.mensajes.cabeza
            while actual_mensaje:
                mensaje = actual_mensaje.valor
                total_mensajes += 1
                if mensaje.clasificacion == "positivo":
                    positivos += 1
                elif mensaje.clasificacion == "negativo":
                    negativos += 1
                else:
                    neutros += 1
                actual_mensaje = actual_mensaje.siguiente
                
            resumen += f"Cantidad total de mensajes recibidos: {total_mensajes}\n"
            resumen += f"Cantidad total de mensajes positivos: {positivos}\n"
            resumen += f"Cantidad total de mensajes negativos: {negativos}\n"
            resumen += f"Cantidad total de mensajes neutros: {neutros}\n\n"
            
            for empresa in self.empresas.iterar():
                total_empresa_mensajes = 0
                total_empresa_positivos = 0
                total_empresa_negativos = 0
                total_empresa_neutros = 0
                actual_mensaje = actual_fecha.valor.mensajes.cabeza
                while actual_mensaje:
                    mensaje = actual_mensaje.valor
                    if empresa.nombre in normalizar_texto(mensaje.contenido):
                        total_empresa_mensajes += 1
                        if mensaje.clasificacion == "positivo":
                            total_empresa_positivos += 1
                        elif mensaje.clasificacion == "negativo":
                            total_empresa_negativos += 1
                        else:
                            total_empresa_neutros += 1
                    actual_mensaje = actual_mensaje.siguiente
                    
                resumen += f"  Empresa: {empresa.nombre}\n"
                resumen += f"    Número total de mensajes que mencionan a Empresa: {total_empresa_mensajes}\n"
                resumen += f"    Mensajes positivos: {total_empresa_positivos}\n"
                resumen += f"    Mensajes negativos: {total_empresa_negativos}\n"
                resumen += f"    Mensajes neutros: {total_empresa_neutros}\n"

                for servicio in empresa.servicios.iterar():
                    total_servicio_mensajes = 0
                    total_servicio_positivos = 0
                    total_servicio_negativos = 0
                    total_servicio_neutros = 0
                    actual_mensaje = actual_fecha.valor.mensajes.cabeza
                    while actual_mensaje:
                        mensaje = actual_mensaje.valor
                        if servicio.se_menciona(mensaje.contenido):
                            total_servicio_mensajes += 1
                            if mensaje.clasificacion == "positivo":
                                total_servicio_positivos += 1
                            elif mensaje.clasificacion == "negativo":
                                total_servicio_negativos += 1
                            else:
                                total_servicio_neutros += 1
                        actual_mensaje = actual_mensaje.siguiente

                    resumen += f"    Servicio: {servicio.nombre}\n"
                    resumen += f"      Número total de mensajes que mencionan al servicio: {total_servicio_mensajes}\n"
                    resumen += f"      Mensajes positivos: {total_servicio_positivos}\n"
                    resumen += f"      Mensajes negativos: {total_servicio_negativos}\n"
                    resumen += f"      Mensajes neutros: {total_servicio_neutros}\n"

            actual_fecha = actual_fecha.siguiente
        return resumen

#---------------- FUNCIONES PYTHON ------------------ 

def leer_mensajes(contenido_archivo):
    root = ET.fromstring(contenido_archivo)
    mensajes = ListaEnlazada()
    
    if root.tag == 'lista_mensajes':
        for mensaje_elem in root.findall('mensaje'):
            mensaje_texto = mensaje_elem.text.strip()
            mensajes.agregar(mensaje_texto)
    else:
        for mensaje_elem in root.findall('.//mensaje'):
            mensaje_texto = mensaje_elem.text.strip()
            mensajes.agregar(mensaje_texto)
            
    return mensajes

def leer_diccionario(contenido_archivo):
    root = ET.fromstring(contenido_archivo)
    palabras = ListaEnlazada()
    
    for palabra in root.find('diccionario').find('sentimientos_positivos').findall('palabra'):
        palabras.agregar(Palabra(normalizar_texto(palabra.text.strip()), 'positivo'))
    
    for palabra in root.find('diccionario').find('sentimientos_negativos').findall('palabra'):
        palabras.agregar(Palabra(normalizar_texto(palabra.text.strip()), 'negativo'))
    
    return palabras

def leer_empresas(contenido_archivo):
    root = ET.fromstring(contenido_archivo)
    empresas = ListaEnlazada()
    
    for empresa_elem in root.find('diccionario').find('empresas_analizar').findall('empresa'):
        nombre_empresa = normalizar_texto(empresa_elem.find('nombre').text.strip())
        empresa = Empresa(nombre_empresa)
        
        for servicio_elem in empresa_elem.find('servicios').findall('servicio'):
            nombre_servicio = normalizar_texto(servicio_elem.get('nombre').strip())
            servicio = Servicio(nombre_servicio)
            
            for alias_elem in servicio_elem.findall('alias'):
                alias = normalizar_texto(alias_elem.text.strip())
                servicio.agregar_alias(alias)
            
            empresa.agregar_servicio(servicio)
        
        empresas.agregar(empresa)
    
    return empresas

def abrir_archivo():
    print("Abriendo el cuadro de diálogo para seleccionar un archivo...")
    ruta = filedialog.askopenfilename(filetypes=[("Archivo XML", "*.xml")])
    if ruta:
        print(f"Archivo seleccionado: {ruta}")
        try:
            with open(ruta, 'r', encoding='utf-8') as file:
                txt = file.read()
                print("Contenido del archivo:")
                print()
                print("--------------------------------------------------")
                print(txt)
                print("--------------------------------------------------")
                print()
                return txt, ruta
            
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            return None
    else:
        print('No se seleccionó ningún archivo.')
        return None

def abrir_archivo_2():
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_uploads = os.path.join(directorio_actual, 'uploads')
    
    if not os.path.exists(ruta_uploads):
        os.makedirs(ruta_uploads)
    
    return abrir_archivo()

'''input_usuario = 'si'
gestor = GestorDatos()
while input_usuario == "si":
    if input_usuario == "si":
        archivo_entrada, ruta = abrir_archivo()
        if archivo_entrada:
            gestor.agregar_mensajes(archivo_entrada)
            gestor.agregar_palabras(archivo_entrada)
            gestor.agregar_empresas(archivo_entrada)

            gestor.mostrar_mensajes()
            gestor.mostrar_palabras()
            gestor.mostrar_empresas()
            gestor.mostrar_resumen()
            gestor.mostrar_resumen_detallado()
            
            opcion_rango_fechas = input("¿Desea filtrar mensajes por rango de fechas? (si/no): ").strip().lower()
            if opcion_rango_fechas == "si":
                fecha_inicio = input("Ingrese la fecha de inicio (dd/mm/aaaa): ").strip()
                fecha_fin = input("Ingrese la fecha de fin (dd/mm/aaaa): ").strip()
                gestor.mostrar_mensajes_por_rango(fecha_inicio, fecha_fin)
            
            opcion_archivo_salida = input("¿Desde generar un archivo XML de salida?: (si/no)").strip()
            if opcion_archivo_salida == 'si':
                gestor.generar_xml_salida()
            
            opcion_mensaje_prueba = input("¿Desea probar un mensaje? (si/no): ").strip().lower()
            if opcion_mensaje_prueba == "si":
                contenido_archivo, ruta = abrir_archivo()
                if contenido_archivo:
                    gestor.prueba_de_mensaje(contenido_archivo, ruta)
            
            opcion_filtrar_mensajes = input("¿Desea filtrar mensajes por fecha y empresa? (si/no): ").strip().lower()
            if opcion_filtrar_mensajes == "si":
                fecha = input("Ingrese la fecha a filtrar (dd/mm/aaaa): ").strip()
                empresa = input("Ingrese el nombre de la empresa a filtrar: ").strip()
                print(f"Mensajes filtrados para la fecha {fecha} y la empresa {empresa}:")
                gestor.filtrar_mensajes(fecha, empresa)
                            
        else:
            print("No se seleccionó ningún archivo.")
    else:
        print("No se cargó ningún archivo.")
'''

#---------------- FUNCIONES FLASK ------------------
gestor = GestorDatos()
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html', contenido_archivo='', archivo_resultante='')

@app.route('/cargar/', methods=['POST'])
def cargar_archivo():
    contenido_archivo = request.form.get('archivo')
    
    if not contenido_archivo:
        return jsonify({"message": "No se ha proporcionado ningún contenido de archivo", "error": True})
    
    gestor.agregar_mensajes(contenido_archivo)
    gestor.agregar_palabras(contenido_archivo)
    gestor.agregar_empresas(contenido_archivo)

    gestor.mostrar_mensajes()
    gestor.mostrar_palabras()
    gestor.mostrar_empresas()

    gestor.mostrar_resumen()
    gestor.mostrar_resumen_detallado()

    gestor.generar_xml_salida()

    ruta_archivo_resultante = os.path.join("uploads", "archivo_salida.xml")
    if not os.path.exists(ruta_archivo_resultante):
        return jsonify({"message": "El archivo resultante no se generó correctamente", "error": True})
    with open(ruta_archivo_resultante, 'r', encoding='utf-8') as f:
        archivo_resultante = f.read()

    return jsonify({"message": "La carga se realizó con éxito.", "error": False, "archivo_resultante": archivo_resultante})

@app.route('/prueba_mensaje/', methods=['POST'])
def prueba_mensaje():
    contenido_archivo = request.form.get('archivo_prueba')
    
    if not contenido_archivo:
        return jsonify({"message": "No se ha proporcionado ningún contenido de archivo", "error": True})
    
    #mmmmm
    ruta_archivo_resultante = os.path.join("uploads", "msjPRUEBA.xml")
    gestor.prueba_de_mensaje(contenido_archivo)
    
    if not os.path.exists(ruta_archivo_resultante):
        return jsonify({"message": "El archivo resultante no se generó correctamente", "error": True})
    with open(ruta_archivo_resultante, 'r', encoding='utf-8') as f:
        archivo_resultante = f.read()
        print(f"contenido del xml: {archivo_resultante}")

    return jsonify({"message": "La carga se realizó con éxito.", "error": False, "archivo_resultante_prueba": archivo_resultante})

@app.route('/limpiar_datos/', methods=['POST'])
def limpiar_datos():
    gestor = GestorDatos()
    gestor.limpiar_datos()    
    gestor.mostrar_mensajes()
    gestor.mostrar_palabras()
    gestor.mostrar_empresas()
    gestor.mostrar_resumen_detallado()
    return jsonify({"message": "Datos limpiados correctamente", "error": False})

@app.route('/lista/', methods=['GET', 'POST'])
def lista():
    gestor.mostrar_mensajes()
    gestor.mostrar_palabras()
    gestor.mostrar_empresas()
    gestor.mostrar_resumen()
    gestor.mostrar_resumen_detallado()
    
    datos_formateados = gestor.formatear_datos()
    return jsonify({"datos_formateados": datos_formateados})
    
    
if __name__ == '__main__':
    app.run(debug=True, port = 8000)
