from django.db import models

class BookModeSession(models.Model):
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=255)
    distractors = models.TextField(blank=True)

    # NEW FIELDS
    order_index = models.IntegerField(default=0)  # play in order
    has_played = models.BooleanField(default=False)  # tracking
    section = models.CharField(max_length=100, blank=True)  # optional grouping
    active = models.BooleanField(default=True)  # allow disabling

    def get_distractor_list(self):
        if not self.distractors:
            return []
        return [d.strip() for d in self.distractors.split('\n') if d.strip()]

    def __str__(self):
        return f"{self.order_index}. {self.question_text[:50]}"


