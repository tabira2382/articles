from rest_framework import serializers
from .models import Like
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['username', 'email', 'password']
    extra_kwargs = {'password': {'write_only': True}}

  def create(self, validated_data):
    user = User.objects.create_user(validated_data['username'], validated_data['email'], validated_data['password'])
    return user
    
class LoginSerializer(serializers.Serializer):
  username = serializers.CharField()
  password = serializers.CharField()

  def validate(self, data):
    user = authenticate(**data)
    if user and user.is_active:
      return user
    raise serializers.ValidationError("Invalid credentials")


class LikeSerializer(serializers.ModelSerializer):
  class Meta:
    model = Like
    fields = ['id' ,'user', 'aricle_id', 'created_at']

class ArticleSerializer(serializers.Serializer):
  id = serializers.CharField()
  title = serializers.CharField()
  url = serializers.URLField()
  tag_list = serializers.CharField()
  likes_count = serializers.IntegerField()

class LikeArticleSerializer(serializers.Serializer):
  article_id = serializers.CharField()