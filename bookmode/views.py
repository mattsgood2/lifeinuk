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

from django.shortcuts import render
from .models import BookModeSession
import random


def book_home(request):
    return render(request, "bookmode/book_home.html", {})


def book_play(request):
    mode = request.GET.get("mode", "normal")  # "normal" or "cant"
    context = {"mode": mode}
    return render(request, "bookmode/book_play.html", context)


def book_listen(request):
    """
    Simple listening drill:
    - walks through all BookModeSession questions in id/order_index order
    - only uses question_text + correct_answer
    - remembers current index in the Django session
    """
    qs = BookModeSession.objects.order_by("id")
    total = qs.count()

    # If there are no questions, just show a message
    if total == 0:
        return render(
            request,
            "bookmode/book_listen.html",
            {
                "question": None,
                "index": 0,
                "total": 0,
                "all_questions": [],
            },
        )

    # Read current index from session
    idx = request.session.get("listen_index", 0)

    # Handle buttons
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "next":
            idx = (idx + 1) % total
        elif action == "prev":
            idx = (idx - 1) % total
        elif action == "reset":
            idx = 0

        request.session["listen_index"] = idx

    # Get the current question
    q = qs[idx]

    context = {
        "question": q,
        "index": idx + 1,      # 1-based for display
        "total": total,
        "all_questions": qs,  # <-- THIS is what Play All needs
    }
    return render(request, "bookmode/book_listen.html", context)

