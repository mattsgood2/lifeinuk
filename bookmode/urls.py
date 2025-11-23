from django.urls import path
# from django.urls import views as bookmode_views
from . import views

urlpatterns = [
    path("", views.book_home, name="book_home"),
    path("play", views.book_play, name="book_play"),
    path("play/<int:question_id>/", views.book_play, name="book_play_question"),
    path("play/", views.book_play, name="book_play"),
    path("listen/", views.book_listen, name="book_listen"),
    # path("sessions/", views.sessions, name="bookmode_sessions"),
    # path("cant_go_wrong/<int:q_id>", views.book_question_strict, name="book_question_strict"),
    # path("question/<int:q_id>/", views.book_question, name="book_question"),
]