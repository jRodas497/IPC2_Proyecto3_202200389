from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.core.files.storage import default_storage
import os
import xmltodict
import requests

# Create your views here.
contenido_archivo = ""

def index(request):
    global contenido_archivo

    if request.method == 'POST' and request.FILES:
        archivo = request.FILES['archivo']
        contenido_archivo = archivo.read().decode("utf-8")
        if contenido_archivo != "":
            json_archivo = xmltodict.parse(contenido_archivo)
            response = requests.post("http://localhost:5000/cargar", json=json_archivo)
            res = response.json()
            print(res["message"])
    
    context = {"contenido": contenido_archivo}
    return render(request, "index.html", context=context)

def cargar(request):
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
            response = requests.post("http://localhost:5000/cargar", json=json_archivo)
            res = response.json()
            
            # Mostrar datos en consola
            print("Contenido del archivo cargado:")
            print(contenido_archivo)
            print("Respuesta del backend Flask:")
            print(res["message"])
            
            return JsonResponse({'message': res["message"], 'error': res["error"], 'contenido_archivo': contenido_archivo})
        else:
            return JsonResponse({'error': 'Formato de archivo no permitido'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def limpiar_datos(request):
    if request.method == 'POST':
        response = requests.post("http://localhost:5000/limpiarDatos")
        res = response.json()
        return JsonResponse({"message": res["message"], "error": res["error"]})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def lista(request):
    if request.method == 'GET':
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        
        response = requests.get(f"http://localhost:5000/resumen?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}")
        res = response.json()
        
        context = {"mensajes": res}
        return render(request, 'lista.html', context=context)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def generar_reporte(request):
    if request.method == 'GET':
        response = requests.get("http://localhost:5000/generarReporte")
        res = response.json()
        return JsonResponse({"message": res["message"], "error": res["error"]})
    return JsonResponse({'error': 'Método no permitido'}, status=405)