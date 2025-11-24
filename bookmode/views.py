from django.shortcuts import render
from .models import BookModeSession


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
    - supports filtering by BookModeSession.section (your 'sub category')
    """

    # ---------- READ SELECTED SECTION FROM REQUEST ----------
    if request.method == "POST":
        selected_category = (request.POST.get("category", "") or "").strip()
    else:
        selected_category = (request.GET.get("category", "") or "").strip()

    # Base queryset: all active sessions
    base_qs = BookModeSession.objects.filter(active=True)

    # Distinct list of sections from BookModeSession itself
    categories = (
        base_qs
        .exclude(section__isnull=True)
        .exclude(section__exact="")
        .values_list("section", flat=True)
        .distinct()
        .order_by("section")
    )

    # Apply section filter if one is chosen
    qs = base_qs
    if selected_category:
        qs = qs.filter(section__iexact=selected_category)

    # Keep your original ordering
    qs = qs.order_by("order_index", "id")

    total = qs.count()

    # No questions at all (or none in this section)
    if total == 0:
        return render(
            request,
            "bookmode/book_listen.html",
            {
                "question": None,
                "index": 0,
                "total": 0,
                "all_questions": [],
                "categories": categories,
                "selected_category": selected_category,
            },
        )

    # ---------- SESSION KEY PER SECTION ----------
    if selected_category:
        session_key = f"book_listen_index_{selected_category}"
    else:
        session_key = "book_listen_index"

    # current index (0-based)
    idx = request.session.get(session_key, 0)

    # ---------- POST ACTIONS: next / prev / reset ----------
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "next":
            idx += 1
        elif action == "prev":
            idx -= 1
        elif action == "reset":
            idx = 0

        # clamp
        if idx < 0:
            idx = 0
        if idx >= total:
            idx = total - 1

        request.session[session_key] = idx

    # extra safety clamp
    if idx >= total:
        idx = total - 1
        request.session[session_key] = idx

    # Current question
    question = qs[idx]

    # ---------- DATA FOR JS "PLAY ALL" ----------
    all_questions = list(
        qs.values("question_text", "correct_answer")
    )

    context = {
        "question": question,
        "index": idx + 1,  # 1-based for display
        "total": total,
        "all_questions": all_questions,
        "categories": categories,
        "selected_category": selected_category,
    }
    return render(request, "bookmode/book_listen.html", context)
