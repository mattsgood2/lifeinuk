from django.contrib import admin
from .models import BookModeSession

@admin.register(BookModeSession)
class BookModeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "short_question", "correct_answer") 
    search_fields = ('question', 'correct_answer')

    def short_question(self, obj):
        return obj.question_text[:60]
    short_question.short_description = "Question"

# Register your models here.
