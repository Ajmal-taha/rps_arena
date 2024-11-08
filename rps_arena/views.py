from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import GameRoom, GamePlayer

def home(request):
    return render(request, 'home.html')

def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            #Authenicate and login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            GamePlayer.objects.create(user = user)
            messages.success(request, 'Sign Up Successfully')
            return redirect('home')
    else:
        form = SignUpForm()
        return render(request, 'sign_up.html', {'form':form})

    return render(request, 'sign_up.html', {'form':form})

@login_required
def leader_boards(request):
    return render(request, 'leader_boards.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        #Authenticate
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in Successfully')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            redirect('login_user')

    return render(request, 'login.html', {})

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, 'you have been logged out')
    return redirect('home')

@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def game(request):
    context = {'game_rooms': GameRoom.objects.all()}
    return render(request, 'game_page.html', context)

@login_required
def game_room(request, room_name):
    
    # Check if the game room already exists
    game_room, created = GameRoom.objects.get_or_create(room_name=room_name)

    # Check if there's space in the room (user_count < 2)
    if game_room.user_count < 2:
        # Add the user to the room if they aren't already in it
        if request.user not in game_room.users.all():
            game_room.users.add(request.user)
            game_room.user_count += 1
            game_room.save()
    else:
        # If room is full, redirect the user and display a message
        messages.error(request, 'Game room already full')
        return redirect(request, 'game_page.html')

    # Render the game room template with room_name and other context
    return render(request, 'game_room.html', {'room_name': room_name})