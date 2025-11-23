# quiz/admin.py
from django.contrib import admin
from django.db.models import Max

from .models import Question
from bookmode.models import BookModeSession  # <- app name 'bookmode' matches your path


@admin.action(description="Copy all Book-Based Questions → Book Listening Mode")
def copy_book_based_to_bookmode(modeladmin, request, queryset=None):

    # 1) Highest existing order_index
    max_order = BookModeSession.objects.aggregate(
        Max('order_index')
    )['order_index__max'] or 0

    order = max_order

    # 2) Existing pairs to avoid duplication
    existing_pairs = set(
        BookModeSession.objects.values_list('question_text', 'correct_answer')
    )

    created = 0

    # 3) All book-based questions from the main Question model
    for q in Question.objects.filter(category='book_based').order_by('id'):

        key = (q.question_text, q.answer_text)
        if key in existing_pairs:
            continue

        order += 1

        BookModeSession.objects.create(
            question_text=q.question_text,
            correct_answer=q.answer_text[:255],
            distractors="",
            order_index=order,
            section=(q.subcategory or "")[:100],
            active=True,
        )

        created += 1

    modeladmin.message_user(
        request,
        f"Successfully copied {created} questions into BookModeSession."
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "category", "subcategory", "topic")
    list_filter = ("category", "topic", "subcategory")
    search_fields = ("question_text", "answer_text")
    actions = [copy_book_based_to_bookmode]   # Action appears in Question admin
