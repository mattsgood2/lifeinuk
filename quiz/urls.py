from django.urls import path, include
from . import views

urlpatterns = [

    path('', views.practice_menu, name='quiz_home'),

    path('practice/', views.practice_menu, name='practice_menu'),
    path('upload/', views.upload_questions, name='quiz_upload'),
    path('quiz/<str:mode>/', views.mc_quiz, name='quiz_mc'),
    path("exam/", views.exam_quiz, name="exam_quiz"),
    path("tts/", views.tts_view, name="tts_view"),
    path('quiz/book_based/', include('bookmode.urls')),
    # path("exam/", views.exam_mode, name="exam_quiz"),
    # path('drill/<str:category>/', views.drill_quiz, name='quiz_drill'),
]
