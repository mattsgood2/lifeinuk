from django.contrib import admin
from django.contrib.sessions.models import Session

from .models import Question


# --------- CUSTOM ACTIONS ---------

@admin.action(description="Mark selected as Book Based (category)")
def make_book_based(modeladmin, request, queryset):
    """
    Bulk-set category='book_based' for selected questions.
    """
    queryset.update(category='book_based')


# --------- QUESTION ADMIN ---------

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "short_text",
        "topic",
        "category",
        "subcategory",
        "theme",
    )

    list_filter = (
        "topic",
        "category",
        "subcategory",
    )

    search_fields = ("question_text", "answer_text", "subcategory")

    ordering = ("topic", "category", "subcategory", "id")

    # These fields you can edit directly in the list view
    list_editable = (
        "theme",
        "category",
        "subcategory",
        "topic",
    )

    # Only our custom action + Django's built-in delete_selected
    actions = [make_book_based]

    def short_text(self, obj):
        return obj.question_text[:80]
    short_text.short_description = "Question"


# --------- SESSIONS (for clearing exam/practice stats) ---------

admin.site.register(Session)