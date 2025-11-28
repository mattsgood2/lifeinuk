# quiz/admin.py
from django.contrib import admin, messages
from django.db import transaction
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


# ------------------ ACTION 1: COPY BOOK QUESTIONS → BOOKMODE ------------------ #

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

        # Clean the answer a bit (strip trailing .?! etc)
        cleaned_answer = (q.answer_text or "").strip().rstrip(".!?").strip()

        if norm_key in existing_by_norm:
            # UPDATE existing BookModeSession
            session = existing_by_norm[norm_key]

            session.question_text = q.question_text
            session.correct_answer = cleaned_answer[:255]
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
                correct_answer=cleaned_answer[:255],
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


# --------------- ACTION 2: CLEAN "(extended variant N)" IN QUIZ --------------- #
@admin.action(description="Clean '(extended variant N)' duplicates in quiz")
def clean_extended_variants(modeladmin, request, queryset):
    """
    Admin action to clean up Question rows like:
      'Some text (Extended Variant 1)'

    Behaviour:
    - If a clean base question exists (without the suffix), delete all variants
      and any extra base duplicates, keep ONE base.
    - If no base exists, rename one variant to the base text and delete the rest.
    """

    # Case-insensitive pattern: '(extended variant 123)' at the end
    pattern = re.compile(r"\s*\(extended variant \d+\)$", re.IGNORECASE)

    # Use iregex so it's also case-insensitive in the DB filter
    variant_qs = list(
        Question.objects.filter(
            question_text__iregex=r"\(extended variant [0-9]+\)$"
        ).order_by("question_text", "id")
    )

    if not variant_qs:
        messages.info(request, "No '(extended variant N)' questions found.")
        return

    # Group by base_text (question without the suffix)
    groups = {}  # base_text -> [variant rows]
    for q in variant_qs:
        base_text = pattern.sub("", q.question_text).strip()
        groups.setdefault(base_text, []).append(q)

    to_delete_ids = []
    changed_count = 0

    with transaction.atomic():
        for base_text, variants in groups.items():
            # Find any existing clean base questions
            base_qs = list(
                Question.objects.filter(question_text=base_text).order_by("id")
            )

            if base_qs:
                # We already have at least one clean base entry
                base = base_qs[0]  # keep this one

                # Any extra base duplicates are redundant
                extra_base_ids = [b.id for b in base_qs[1:]]

                # All these variant rows are redundant too
                variant_ids = [v.id for v in variants]

                to_delete_ids.extend(extra_base_ids + variant_ids)

            else:
                # No clean base exists:
                # - keep the first variant, rename it to the base text
                # - delete the rest
                keeper = variants[0]
                if keeper.question_text != base_text:
                    keeper.question_text = base_text
                    keeper.save(update_fields=["question_text"])
                    changed_count += 1

                extra_variant_ids = [v.id for v in variants[1:]]
                to_delete_ids.extend(extra_variant_ids)

        deleted = Question.objects.filter(id__in=to_delete_ids).delete()[0]

    messages.success(
        request,
        f"Cleaned extended variants: converted {changed_count} questions, "
        f"deleted {deleted} redundant rows."
    )

# ------------------------------ QUESTION ADMIN ------------------------------- #

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "category", "subcategory", "topic")
    list_filter = ("category", "topic", "subcategory")
    search_fields = ("question_text", "answer_text")

    # BOTH actions available on the Question admin
    actions = [copy_book_based_to_bookmode, clean_extended_variants]
