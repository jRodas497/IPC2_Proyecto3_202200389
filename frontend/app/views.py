from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from io import BytesIO
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
            
            return JsonResponse({'message': res["message"], 'error': res["error"], 'contenido_archivo': contenido_archivo, 'archivo_resultante': res.get('archivo_resultante', ''), 'datos_formateados': res.get('datos_formateados', '')})
        else:
            return JsonResponse({'error': 'Formato de archivo no permitido'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def prueba_mensaje(request):
    if request.method == 'POST':
        if 'archivo_prueba' not in request.FILES:
            return JsonResponse({'error': 'No se ha seleccionado ningún archivo'}, status=400)

        archivo = request.FILES['archivo_prueba']
        
        if archivo.name == '':
            return JsonResponse({'error': 'No se ha seleccionado ningún archivo'}, status=400)    

        if archivo and archivo.name.endswith('.xml'):
            contenido_archivo_prueba = archivo.read().decode("utf-8")
            json_archivo = xmltodict.parse(contenido_archivo_prueba)

            response = requests.post("http://localhost:8000/prueba_mensaje", json=json_archivo)
            res = response.json()
            
            print("Contenido del archivo cargado:")
            print(contenido_archivo_prueba)
            print("Respuesta del backend Flask:")
            print(res["message"])
            
            return JsonResponse({'message': res["message"], 'error': res["error"], 'contenido_archivo_prueba': contenido_archivo_prueba, 'archivo_resultante_prueba': res.get('archivo_resultante_prueba', '')})
        else:
            return JsonResponse({'error': 'Formato de archivo no permitido'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def generar_pdf(request):
    response = requests.get('http://localhost:8000/generar_pdf/')
    if response.status_code == 200:
        return HttpResponse(response.content, content_type='application/pdf')
    else:
        return JsonResponse({"message": "Error al generar el PDF", "error": True})

def limpiar_datos(request):
    if request.method == 'POST':
        response = requests.post("http://localhost:8000/limpiar_datos")
        res = response.json()
        return JsonResponse({"message": res["message"], "error": res["error"]})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def lista(request):
    if request.method == 'GET':
        response = requests.get('http://localhost:8000/lista/')
        res = response.json()
        
        return render(request, 'lista.html', {
        "datos_formateados": res['datos_formateados']
    })
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def mostrar_mensajes_por_rango(request):
    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            return JsonResponse({"message": "No se han proporcionado ambas fechas", "error": True})
        
        response = requests.post('http://localhost:8000/mostrar_mensajes_por_rango/', data={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
        if response.status_code == 200:
            return HttpResponse(response.content, content_type='application/pdf')
        else:
            return JsonResponse({"message": "Error al generar el PDF", "error": True})
     
def resumen_clasificacion_por_fecha(request):
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        empresa = request.POST.get('empresa')
        
        if not fecha:
            return JsonResponse({"message": "No se ha proporcionado la fecha", "error": True})
        
        response = requests.post('http://localhost:8000/resumen_clasificacion_por_fecha/', data={'fecha': fecha, 'empresa': empresa})
        if response.status_code == 200:
            data = response.json()
            if data.get("error"):
                return JsonResponse({"message": data["message"], "error": True})
            return JsonResponse({"message": data["message"], "image_path": data["image_path"], "error": False})
        else:
            return JsonResponse({"message": "Error al generar el resumen", "error": True})