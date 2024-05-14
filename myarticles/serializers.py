from rest_framework import serializers
from .models import Like

class LikeSerializer(serializers.ModelSerializer):
  class Meta:
    model = Like
    fields = ['user', 'aricle_id', 'created_at']

class ArticleSerializer(serializers.Serializer):
  id = serializers.CharField()
  title = serializers.CharField()
  url = serializers.URLField()
  tag_list = serializers.CharField()
  likes_count = serializers.IntegerField()