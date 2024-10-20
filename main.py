import string
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

class Palabra:
    def __init__(self, texto, tipo):
        self.texto = texto
        self.tipo = tipo

class Servicio:
    def __init__(self, nombre):
        self.nombre = nombre
        self.aliases = ListaEnlazada()

    def agregar_alias(self, alias):
        if not self.aliases.contiene(alias):
            self.aliases.agregar(alias)
        else:
            print(f"Alias repetido: {alias}")

class Empresa:
    def __init__(self, nombre):
        self.nombre = nombre
        self.servicios = ListaEnlazada()

    def agregar_servicio(self, servicio):
        if not self.servicios.contiene(servicio, key=lambda x: x.nombre):
            self.servicios.agregar(servicio)
        else:
            print(f"El servicio {servicio.nombre} ya existe en la empresa {self.nombre}")

class GestorDatos:
    def __init__(self):
        self.mensajes = ListaEnlazada()
        self.palabras_positivas = ListaEnlazada()
        self.palabras_negativas = ListaEnlazada()
        self.empresas = ListaEnlazada()

    def agregar_mensajes(self, archivo):
        nuevos_mensajes = leer_mensajes(archivo)
        for mensaje in nuevos_mensajes.iterar():
            self.mensajes.agregar(mensaje)

    def agregar_palabras(self, archivo):
        nuevas_palabras = leer_diccionario(archivo)
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
            
    def agregar_empresas(self, archivo):
        nuevas_empresas = leer_empresas(archivo)
        for empresa in nuevas_empresas.iterar():
            if not self.empresas.contiene(empresa, key=lambda x: x.nombre):
                self.empresas.agregar(empresa)
            else:
                print(f"Empresa repetida: {empresa.nombre}")
                
        print('-' * 50)

    def mostrar_mensajes(self):
        print("Mensajes:")
        for texto in self.mensajes.iterar():
            try:
                mensaje = Mensaje.parsear_mensaje(texto)
                mensaje.analizar_sentimientos(self.palabras_positivas, self.palabras_negativas)
                print(f"Lugar: {mensaje.lugar}")
                print(f"Fecha: {mensaje.fecha}")
                print(f"Hora: {mensaje.hora}")
                print(f"Usuario: {mensaje.usuario}")
                print(f"Red Social: {mensaje.red_social}")
                print(f"Contenido: {mensaje.contenido}")
                print(f"Palabras Positivas: {mensaje.positivas}")
                print(f"Palabras Negativas: {mensaje.negativas}")
                print(f"Clasificación: {mensaje.clasificacion}")
                print("------")
            except ValueError as e:
                print(f"Error al parsear mensaje: {e}")

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

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    return texto

def leer_mensajes(archivo):
    tree = ET.parse(archivo)
    root = tree.getroot()
    mensajes = ListaEnlazada()
    for mensaje in root.find('lista_mensajes').findall('mensaje'):
        mensajes.agregar(mensaje.text.strip())
    return mensajes

def leer_diccionario(archivo):
    tree = ET.parse(archivo)
    root = tree.getroot()
    palabras = ListaEnlazada()
    
    for palabra in root.find('diccionario').find('sentimientos_positivos').findall('palabra'):
        palabras.agregar(Palabra(normalizar_texto(palabra.text.strip()), 'positivo'))
    
    for palabra in root.find('diccionario').find('sentimientos_negativos').findall('palabra'):
        palabras.agregar(Palabra(normalizar_texto(palabra.text.strip()), 'negativo'))
    
    return palabras

def leer_empresas(archivo):
    tree = ET.parse(archivo)
    root = tree.getroot()
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
            
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            
        return ruta

gestor = GestorDatos()

input_usuario = 'si'

while input_usuario == "si":
    input_usuario = input("¿Desea cargar un archivo XML? (si/no): ").strip().lower()
    if input_usuario == "si":
        archivo_entrada = abrir_archivo()
        if archivo_entrada:
            gestor.agregar_mensajes(archivo_entrada)
            gestor.agregar_palabras(archivo_entrada)
            gestor.agregar_empresas(archivo_entrada)

            gestor.mostrar_mensajes()
            gestor.mostrar_palabras()
            gestor.mostrar_empresas()
        else:
            print("No se seleccionó ningún archivo.")
    else:
        print("No se cargó ningún archivo.")
# archivo_entrada2 = abrir_archivo()
# gestor.agregar_mensajes(archivo_entrada2)
# gestor.agregar_palabras(archivo_entrada2)

# Mostrar datos actualizados
# gestor.mostrar_mensajes()
# gestor.mostrar_palabras()