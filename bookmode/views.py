from django.shortcuts import render, get_object_or_404
from .models import BookModeSession
import random
# bookmode/views.py
from django.shortcuts import render


def book_home(request):
    return render(request, "bookmode/book_home.html", {})

def book_play(request):
    mode = request.GET.get("mode", "normal")  # "normal" or "cant"
    context = {"mode": mode}
    return render(request, "bookmode/book_play.html", context)

def book_listen(request):
    """
    Listening drill:
    - walks through all BookModeSession questions in order_index (then id)
    - uses question_text + correct_answer
    - remembers current index in the Django session
    """
    qs = BookModeSession.objects.filter(active=True).order_by("order_index", "id")
    total = qs.count()

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

    # current index stored in the session (0-based)
    idx = request.session.get("book_listen_index", 0)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "next":
            idx += 1
        elif action == "prev":
            idx -= 1
        elif action == "reset":
            idx = 0

        # clamp into valid range
        if idx < 0:
            idx = 0
        if idx >= total:
            idx = total - 1

        request.session["book_listen_index"] = idx

    question = qs[idx]

    # 👈 NEW: compact list of all questions for JS
    all_questions = list(
        qs.values("question_text", "correct_answer")
    )

    context = {
        "question": question,
        "index": idx + 1,      # 1-based for display
        "total": total,
        "all_questions": all_questions,
    }
    return render(request, "bookmode/book_listen.html", context)