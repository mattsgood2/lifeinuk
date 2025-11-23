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
    - walks through all BookModeSession questions in id order
    - only uses question + correct_answer
    - remembers current index in the Django session
    """

    qs = BookModeSession.objects.order_by("id")
    total = qs.count()

    if total == 0:
        return render(
            request,
            "bookmode/book_listen.html",
            {"question": None, "index": 0, "total": 0},
        )

    # read current index from the session (per browser)
    idx = request.session.get("book_listen_index", 0)

    # handle buttons
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "next":
            idx += 1
        elif action == "prev":
            idx -= 1
        elif action == "reset":
            idx = 0

        # keep in range
        if idx < 0:
            idx = 0
        if idx >= total:
            idx = total - 1

        request.session["book_listen_index"] = idx

    # fetch the question for the (possibly updated) index
    question = qs[idx]

    context = {
        "question": question,
        "index": idx + 1,  # 1-based for display
        "total": total,
    }
    return render(request, "bookmode/book_listen.html", context)

