from django.db import models
from django.contrib.auth.models import User

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    article_id = models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article_id')

    def __str__(self):
        return f"{self.user.username} likes {self.article_id}"