from django.db import models

# Create your models here.
class BookModeSession(models.Model):
    question = models.TextField()
    correct_answer = models.CharField(max_length=255)
    distractors = models.TextField(blank=True)

    def get_distractor_list(self):
        if not self.distractors:
            return []
        return [d.strip() for d in self.distractors.split('\n') if d.strip()]