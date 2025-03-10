from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sign_up/', views.sign_up, name='sign_up'),
    path('leader_boards/', views.leader_boards, name='leader_boards'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('game/', views.game, name='game'),
    path('search-game-rooms/', views.search_game_rooms, name='search_game_rooms'),
    path('game/<str:room_name>/', views.game_room, name='game_room'),
]