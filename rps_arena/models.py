from django.contrib.auth.models import User
from django.db import models

class GamePlayer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

class GameRoom(models.Model):
    room_name = models.CharField(max_length=100, unique=True)
    user_count = models.PositiveIntegerField(default=0)
    users = models.ManyToManyField(User, related_name="game_rooms")

    def __str__(self):
        return self.room_name
