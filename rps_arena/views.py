from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm

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
            messages.success(request, 'Sign Up Successfully')
            return redirect('home')
    else:
        form = SignUpForm()
        return render(request, 'sign_up.html', {'form':form})

    return render(request, 'sign_up.html', {'form':form})

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

def logout_user(request):
    logout(request)
    messages.success(request, 'you have been logged out')
    return redirect('home')

def profile(request):
    return render(request, 'profile.html')

def game(request):
    return render(request, 'game_page.html')

def game_room(request, room_name):
    return render(request, 'game_room.html', {'room_name': room_name})