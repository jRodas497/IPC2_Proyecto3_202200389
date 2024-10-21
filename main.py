import os
from xml.dom.minidom import Document
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

class Palabra:
    def __init__(self, texto, tipo):
        self.texto = texto
        self.tipo = tipo

class Servicio:
    def __init__(self, nombre):
        self.nombre = nombre
        self.aliases = ListaEnlazada()
        self.total_mensajes = 0
        self.mensajes_positivos = 0
        self.mensajes_negativos = 0
        self.mensajes_neutros = 0

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

class FechaMensajes:
    def __init__(self, fecha):
        self.fecha = fecha
        self.mensajes = ListaEnlazada()
        self.siguiente = None

    def agregar_mensaje(self, mensaje):
        self.mensajes.agregar(mensaje)

class MensajesPorFecha:
    def __init__(self):
        self.cabeza = None

    def agregar_mensaje(self, fecha, mensaje):
        if not self.cabeza:
            self.cabeza = FechaMensajes(fecha)
            self.cabeza.agregar_mensaje(mensaje)
        else:
            actual = self.cabeza
            while actual:
                if actual.fecha == fecha:
                    actual.agregar_mensaje(mensaje)
                    return
                if not actual.siguiente:
                    break
                actual = actual.siguiente
            nuevo_nodo = FechaMensajes(fecha)
            nuevo_nodo.agregar_mensaje(mensaje)
            actual.siguiente = nuevo_nodo

class GestorDatos:
    def __init__(self):
        self.mensajes = ListaEnlazada()
        self.palabras_positivas = ListaEnlazada()
        self.palabras_negativas = ListaEnlazada()
        self.empresas = ListaEnlazada()
        self.mensajes_por_fecha = MensajesPorFecha()


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

        actual_fecha = self.mensajes_por_fecha.cabeza
        while actual_fecha:
            print("*****" * 5 )
            print(f"Fecha: {actual_fecha.fecha}")
            print("*****" * 5 )
            actual_mensaje = actual_fecha.mensajes.cabeza
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
        actual_fecha = self.mensajes_por_fecha.cabeza
        while actual_fecha:
            print(f"FECHA: {actual_fecha.fecha}")
            total_mensajes = 0
            positivos = 0
            negativos = 0
            neutros = 0
            actual_mensaje = actual_fecha.mensajes.cabeza
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
                actual_mensaje = actual_fecha.mensajes.cabeza
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
                    actual_mensaje = actual_fecha.mensajes.cabeza
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

    def generar_xml_salida(self, archivo_salida):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        
        ruta_uploads = os.path.join(directorio_actual, 'uploads')
        if not os.path.exists(ruta_uploads):
            os.makedirs(ruta_uploads)

        archivo_salida = os.path.join(ruta_uploads, archivo_salida)

        doc = Document()
        root = doc.createElement("lista_respuestas")
        doc.appendChild(root)

        actual_fecha = self.mensajes_por_fecha.cabeza
        while actual_fecha:
            respuesta = doc.createElement("respuesta")
            root.appendChild(respuesta)

            fecha = doc.createElement("fecha")
            fecha.appendChild(doc.createTextNode(actual_fecha.fecha))
            respuesta.appendChild(fecha)

            mensajes = doc.createElement("mensajes")
            respuesta.appendChild(mensajes)

            total_mensajes = 0
            positivos = 0
            negativos = 0
            neutros = 0
            actual_mensaje = actual_fecha.mensajes.cabeza
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

                total_empresa_mensajes = 0
                total_empresa_positivos = 0
                total_empresa_negativos = 0
                total_empresa_neutros = 0
                actual_mensaje = actual_fecha.mensajes.cabeza
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

                total_empresa_elem = doc.createElement("total")
                total_empresa_elem.appendChild(doc.createTextNode(str(total_empresa_mensajes)))
                mensajes_empresa.appendChild(total_empresa_elem)

                positivos_empresa_elem = doc.createElement("positivos")
                positivos_empresa_elem.appendChild(doc.createTextNode(str(total_empresa_positivos)))
                mensajes_empresa.appendChild(positivos_empresa_elem)

                negativos_empresa_elem = doc.createElement("negativos")
                negativos_empresa_elem.appendChild(doc.createTextNode(str(total_empresa_negativos)))
                mensajes_empresa.appendChild(negativos_empresa_elem)

                neutros_empresa_elem = doc.createElement("neutros")
                neutros_empresa_elem.appendChild(doc.createTextNode(str(total_empresa_neutros)))
                mensajes_empresa.appendChild(neutros_empresa_elem)

                servicios_elem = doc.createElement("servicios")
                empresa_elem.appendChild(servicios_elem)

                for servicio in empresa.servicios.iterar():
                    servicio_elem = doc.createElement("servicio")
                    servicio_elem.setAttribute("nombre", servicio.nombre)
                    servicios_elem.appendChild(servicio_elem)

                    mensajes_servicio = doc.createElement("mensajes")
                    servicio_elem.appendChild(mensajes_servicio)

                    total_servicio_mensajes = 0
                    total_servicio_positivos = 0
                    total_servicio_negativos = 0
                    total_servicio_neutros = 0
                    actual_mensaje = actual_fecha.mensajes.cabeza
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

                    total_servicio_elem = doc.createElement("total")
                    total_servicio_elem.appendChild(doc.createTextNode(str(total_servicio_mensajes)))
                    mensajes_servicio.appendChild(total_servicio_elem)

                    positivos_servicio_elem = doc.createElement("positivos")
                    positivos_servicio_elem.appendChild(doc.createTextNode(str(total_servicio_positivos)))
                    mensajes_servicio.appendChild(positivos_servicio_elem)

                    negativos_servicio_elem = doc.createElement("negativos")
                    negativos_servicio_elem.appendChild(doc.createTextNode(str(total_servicio_negativos)))
                    mensajes_servicio.appendChild(negativos_servicio_elem)

                    neutros_servicio_elem = doc.createElement("neutros")
                    neutros_servicio_elem.appendChild(doc.createTextNode(str(total_servicio_neutros)))
                    mensajes_servicio.appendChild(neutros_servicio_elem)

            actual_fecha = actual_fecha.siguiente

        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent="  "))

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
            gestor.mostrar_resumen()
            gestor.mostrar_resumen_detallado()
            
            archivo_salida = input("Ingrese el nombre del archivo de salida: ").strip()
            gestor.generar_xml_salida(archivo_salida)
        else:
            print("No se seleccionó ningún archivo.")
    else:
        print("No se cargó ningún archivo.")