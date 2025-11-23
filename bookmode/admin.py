# bookmode/admin.py
from django.contrib import admin

from .models import BookModeSession


@admin.register(BookModeSession)
class BookModeSessionAdmin(admin.ModelAdmin):
    list_display = ("order_index", "question_text", "section", "active")
    list_editable = ("active", "section",)
    search_fields = ("question_text", "correct_answer")
