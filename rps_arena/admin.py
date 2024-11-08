from django.contrib import admin
from .models import GameRoom, GamePlayer

class GameRoomAdmin(admin.ModelAdmin):
    list_display = ('room_name', 'user_count')
    search_fields = ('room_name',)

class GamePlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'points')
    search_fields = ('user',)

# Register the model with the custom admin class
admin.site.register(GameRoom, GameRoomAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)
