from django.contrib import admin
from .models import BookModeSession

@admin.register(BookModeSession)
class BookModeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "correct_answer") 
    search_fields = ('question', 'correct_answer')

# Register your models here.
