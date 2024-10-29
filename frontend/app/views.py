from django.shortcuts import render
from django.http import JsonResponse
import requests
import xmltodict

contenido_archivo = ""

def index(request):
    global contenido_archivo

    if request.method == 'POST' and request.FILES:
        archivo = request.FILES['archivo']
        contenido_archivo = archivo.read().decode("utf-8")
        if contenido_archivo != "":
            json_archivo = xmltodict.parse(contenido_archivo)
            response = requests.post("http://localhost:8000/cargar", json=json_archivo)
            res = response.json()
            print(res["message"])
    
    context = {"contenido": contenido_archivo}
    return render(request, "index.html", context=context)

def cargar_archivo(request):
    if request.method == 'POST':
        if 'archivo' not in request.FILES:
            return JsonResponse({'error': 'No se ha seleccionado ningún archivo'}, status=400)
        
        archivo = request.FILES['archivo']
        
        if archivo.name == '':
            return JsonResponse({'error': 'No se ha seleccionado ningún archivo'}, status=400)
        
        if archivo and archivo.name.endswith('.xml'):
            contenido_archivo = archivo.read().decode("utf-8")
            json_archivo = xmltodict.parse(contenido_archivo)
            
            # Enviar los datos al backend Flask
            response = requests.post("http://localhost:8000/cargar", json=json_archivo)
            res = response.json()
            
            # Mostrar datos en consola
            print("Contenido del archivo cargado:")
            print(contenido_archivo)
            print("Respuesta del backend Flask:")
            print(res["message"])
            
            return JsonResponse({'message': res["message"], 'error': res["error"], 'contenido_archivo': contenido_archivo, 'archivo_resultante': res.get('archivo_resultante', '')})
        else:
            return JsonResponse({'error': 'Formato de archivo no permitido'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def limpiar_datos(request):
    if request.method == 'POST':
        response = requests.post("http://localhost:8000/limpiar_datos")
        res = response.json()
        return JsonResponse({"message": res["message"], "error": res["error"]})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def lista(request):
    fecha = request.GET.get('fecha')
    empresa = request.GET.get('empresa')
    
    params = {}
    if fecha:
        params['fecha'] = fecha
    if empresa:
        params['empresa'] = empresa
    
    response = requests.get('http://localhost:8000/lista/', params=params)
    data = response.json()
    
    return JsonResponse({
        "empresas": data['empresas'],
        "mensajes": data['mensajes'],
        "total_mensajes": data['total_mensajes'],
        "positivos": data['positivos'],
        "negativos": data['negativos'],
        "neutros": data['neutros']
    })

def generar_reporte(request):
    if request.method == 'GET':
        response = requests.get("http://localhost:8000/generar_reporte")
        res = response.json()
        return JsonResponse({"message": res["message"], "error": res["error"]})
    return JsonResponse({'error': 'Método no permitido'}, status=405)