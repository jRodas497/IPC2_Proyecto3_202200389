"""
URL configuration for frontend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cargar/', views.cargar_archivo, name='cargar_archivo'),
    path('prueba_mensaje/', views.prueba_mensaje, name='prueba_mensaje'),
    path('limpiar_datos/', views.limpiar_datos, name='limpiar_datos'),
    path('lista/', views.lista, name='lista'),
    path('generar_pdf/', views.generar_pdf, name='generar_pdf'),
    path('mostrar_mensajes_por_rango/', views.mostrar_mensajes_por_rango, name='mostrar_mensajes_por_rango'),
    path('resumen_clasificacion_por_fecha/', views.resumen_clasificacion_por_fecha, name='resumen_clasificacion_por_fecha'),
]