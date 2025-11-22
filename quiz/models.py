from django.db import models

class Question(models.Model):
    TOPIC_CHOICES = [
        ('history', 'History'),
        ('government', 'Government & Politics'),
        ('culture', 'Culture & Society'),
        ('geography', 'Geography & Places'),
        ('other', 'Other'),
    ]
    CATEGORY_CHOICES = [
        ('book_based', 'Book Based'),
        ('general', 'General'),
        ('hardest', 'Hardest'),
        ('cheatsheet', 'Cheat Sheet'),
        ('common', 'Common Questions'),
        
    ]
    THEME_CHOICES = [
        ('kings', 'Kings & Queens'),
        ('wars', 'Wars'),
        ('gov', 'Government'),
        ('geo', 'Geography'),
        ('mixed', 'Random'),
        ('other', 'Other'),
    ]

    question_text = models.TextField()
    subcategory = models.CharField(max_length=200, blank=True, null=True)
    answer_text = models.TextField()
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='other')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, blank=True, null=True, help_text="(Kings, Wars, Gov...ect)",
    )


    
    # def __str__(self):
    #     return self.question_text[:80]
    
    def __str__(self):
        return f"[{self.category} / {self.subcategory}] {self.question_text[:80]}"
