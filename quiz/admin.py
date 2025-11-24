# quiz/admin.py
from django.contrib import admin
from django.db.models import Max
import re

from .models import Question
from bookmode.models import BookModeSession  # <- app name 'bookmode' matches your app


def normalise(text: str) -> str:
    """
    Normalise question text so small changes (like trailing full stop)
    don't create duplicates.
    """
    if not text:
        return ""
    t = text.strip()
    t = t.rstrip(".")                 # remove final "."
    t = re.sub(r"\s+", " ", t)        # collapse multiple spaces
    return t.lower()


@admin.action(description="Copy all Book-Based Questions → Book Listening Mode")
def copy_book_based_to_bookmode(modeladmin, request, queryset=None):
    """
    Sync book-based questions from Question -> BookModeSession.

    - Updates existing BookModeSession rows if the (normalised) question matches.
    - Creates new ones for genuinely new questions.
    - Does NOT duplicate questions on repeated runs.
    """

    # 1) Highest existing order_index so new ones go at the end
    max_order = BookModeSession.objects.aggregate(
        Max('order_index')
    )['order_index__max'] or 0

    order = max_order

    # 2) Map existing sessions by normalised question text
    existing_by_norm = {}
    for b in BookModeSession.objects.all():
        key = normalise(b.question_text)
        if key:
            existing_by_norm[key] = b

    created = 0
    updated = 0

    # 3) Decide which questions to process:
    #    - If admin selected some, use queryset
    #    - Otherwise, take all book_based questions
    if queryset is not None and queryset.exists():
        qs = queryset
    else:
        qs = Question.objects.filter(category="book_based")

    # 4) Process questions in a stable order
    for q in qs.order_by("id"):
        norm_key = normalise(q.question_text)

        if norm_key in existing_by_norm:
            # UPDATE existing BookModeSession
            session = existing_by_norm[norm_key]

            session.question_text = q.question_text
            session.correct_answer = q.answer_text[:255]
            session.distractors = ""
            session.section = (q.subcategory or "")[:100]
            session.active = True
            # keep existing order_index so order doesn’t jump around
            session.save()
            updated += 1

        else:
            # CREATE new BookModeSession
            order += 1
            session = BookModeSession.objects.create(
                question_text=q.question_text,
                correct_answer=q.answer_text[:255],
                distractors="",
                order_index=order,
                section=(q.subcategory or "")[:100],
                active=True,
            )
            created += 1
            existing_by_norm[norm_key] = session

    modeladmin.message_user(
        request,
        f"Synced book-based questions: {created} created, {updated} updated."
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "category", "subcategory", "topic")
    list_filter = ("category", "topic", "subcategory")
    search_fields = ("question_text", "answer_text")
    actions = [copy_book_based_to_bookmode]   # <-- action appears in Question admin
