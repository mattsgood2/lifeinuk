from django.shortcuts import render, get_object_or_404
from .models import BookModeSession
import random
# bookmode/views.py
from django.shortcuts import render

def book_home(request):
    return render(request, "bookmode/book_home.html", {})

def book_play(request):
    mode = request.GET.get("mode", "normal")  # "normal" or "cant"
    context = {
        "mode": mode,
    }
    return render(request, "bookmode/book_play.html", context)