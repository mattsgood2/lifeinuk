from django import forms
from .models import Question

class UploadFileForm(forms.Form):
    file = forms.FileField(label="Upload Q&A text file")
    topic = forms.ChoiceField(choices=Question.TOPIC_CHOICES, label="Topic")
    category = forms.ChoiceField(choices=Question.CATEGORY_CHOICES, label="Category")
