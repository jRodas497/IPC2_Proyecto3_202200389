import re
from tkinter import filedialog
import xml.etree.ElementTree as ET
import unicodedata

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

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    return texto

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
            
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            
        return ruta

class Mensaje:
    def __init__(self, lugar, fecha, hora, usuario, red_social, contenido):
        self.lugar = lugar
        self.fecha = fecha
        self.hora = hora
        self.usuario = usuario
        self.red_social = red_social
        self.contenido = contenido

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

class AnalizadorSentimientos:
    def __init__(self, diccionario_sentimientos, diccionario_empresas):
        self.diccionario_sentimientos = diccionario_sentimientos
        self.diccionario_empresas = diccionario_empresas

    def analizar_sentimiento(self, mensaje):
        palabras = mensaje.contenido.split()
        positivas = sum(1 for palabra in palabras if normalizar_texto(palabra) in self.diccionario_sentimientos['positivas'])
        negativas = sum(1 for palabra in palabras if normalizar_texto(palabra) in self.diccionario_sentimientos['negativas'])

        if positivas > negativas:
            return "positivo"
        elif negativas > positivas:
            return "negativo"
        else:
            return "neutro"

    def asociar_con_empresa(self, mensaje):
        empresas_mencionadas = ListaEnlazada()
        for empresa, servicios in self.diccionario_empresas.items():
            if normalizar_texto(empresa) in normalizar_texto(mensaje.contenido):
                empresas_mencionadas.agregar(empresa)
            for servicio in servicios.iterar():
                if normalizar_texto(servicio) in normalizar_texto(mensaje.contenido):
                    empresas_mencionadas.agregar(servicio)
        return empresas_mencionadas

class AlmacenamientoXML:
    def __init__(self, archivo_xml):
        self.archivo_xml = archivo_xml
        self.root = ET.Element("lista_respuestas")

    def almacenar_mensaje(self, mensaje):
        respuesta_element = ET.SubElement(self.root, "respuesta")
        ET.SubElement(respuesta_element, "fecha").text = mensaje.fecha.split()[0]
        ET.SubElement(respuesta_element, "lugar").text = mensaje.lugar
        ET.SubElement(respuesta_element, "usuario").text = mensaje.usuario
        ET.SubElement(respuesta_element, "red_social").text = mensaje.red_social
        ET.SubElement(respuesta_element, "contenido").text = mensaje.contenido

    def guardar_xml(self):
        tree = ET.ElementTree(self.root)
        tree.write(self.archivo_xml, encoding='utf-8', xml_declaration=True)

    def mostrar_xml(self):
        tree = ET.ElementTree(self.root)
        ET.dump(tree)

# Funciones auxiliares
def leer_mensajes(archivo):
    tree = ET.parse(archivo)
    root = tree.getroot()
    mensajes = ListaEnlazada()
    for mensaje in root.find('lista_mensajes').findall('mensaje'):
        mensajes.agregar(mensaje.text.strip())
    return mensajes

def cargar_diccionarios(archivo):
    tree = ET.parse(archivo)
    root = tree.getroot()
    diccionario_sentimientos = {
        'positivas': ListaEnlazada(),
        'negativas': ListaEnlazada()
    }
    for palabra in root.find('diccionario').find('sentimientos_positivos').findall('palabra'):
        diccionario_sentimientos['positivas'].agregar(normalizar_texto(palabra.text.strip()))
    for palabra in root.find('diccionario').find('sentimientos_negativos').findall('palabra'):
        diccionario_sentimientos['negativas'].agregar(normalizar_texto(palabra.text.strip()))

    diccionario_empresas = {}
    for empresa in root.find('diccionario').find('empresas_analizar').findall('empresa'):
        nombre_empresa = normalizar_texto(empresa.find('nombre').text.strip())
        servicios = ListaEnlazada()
        for servicio in empresa.find('servicios').findall('servicio'):
            servicios.agregar(normalizar_texto(servicio.get('nombre').strip()))
            for alias in servicio.findall('alias'):
                servicios.agregar(normalizar_texto(alias.text.strip()))
        diccionario_empresas[nombre_empresa] = servicios

    return diccionario_sentimientos, diccionario_empresas

# Ejemplo de uso
archivo_entrada = abrir_archivo()
mensajes = leer_mensajes(archivo_entrada)

for texto in mensajes.iterar():
    try:
        mensaje = Mensaje.parsear_mensaje(texto)
        print(f"Lugar: {mensaje.lugar}")
        print(f"Fecha: {mensaje.fecha}")
        print(f"Hora: {mensaje.hora}")
        print(f"Usuario: {mensaje.usuario}")
        print(f"Red Social: {mensaje.red_social}")
        print(f"Contenido: {mensaje.contenido}")
        print("------")
    except ValueError as e:
        print(f"Error al parsear mensaje: {e}")