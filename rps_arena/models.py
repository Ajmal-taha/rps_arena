from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator

class GamePlayer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    wins = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    losses = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    draws = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    matches_played = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def __str__(self):
        return self.user.username
    
    # method which automatically creates GamePlayer when a new User is created
    @receiver(post_save, sender=User)
    def create_game_player(sender, instance, created, **kwargs):
        if created:
            GamePlayer.objects.create(user=instance)

class GameRoom(models.Model):
    room_name = models.CharField(max_length=100, unique=True)
    user_count = models.PositiveIntegerField(default=0)
    users = models.ManyToManyField(User, related_name="game_rooms")

    def __str__(self):
        return self.room_name
