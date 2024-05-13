from ..models import Like
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from ..serializers import LikeSerializer

class LikeList(APIView):
    def get(self, request, format=None):
        likes = Like.objects.all()
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)