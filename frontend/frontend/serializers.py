from rest_framework import serializers

class MensajeSerializer(serializers.Serializer):
    fecha = serializers.CharField(max_length=10)
    lugar = serializers.CharField(max_length=100)
    hora = serializers.CharField(max_length=10)
    usuario = serializers.CharField(max_length=100)
    red_social = serializers.CharField(max_length=50)
    contenido = serializers.CharField()
    clasificacion = serializers.CharField(max_length=20)