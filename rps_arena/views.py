from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def home(request):
    return render(request, 'home.html')

def sign_up(request):
    return render(request, 'sign_up.html')

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