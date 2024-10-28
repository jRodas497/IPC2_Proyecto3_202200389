from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cargar/', views.cargar_archivo, name='cargar_archivo'),
    path('limpiar_datos/', views.limpiar_datos, name='limpiar_datos'),
    path('resumen/', views.resumen, name='resumen'),
    path('generar_reporte/', views.generar_reporte, name='generar_reporte'),
]