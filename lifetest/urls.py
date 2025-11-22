from django.contrib import admin
from bookmode import views as bookmode_views
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls')),

    path("", RedirectView.as_view(url="/quiz/practice/", permanent=False)),

    path('book_home/', include('bookmode.urls')),
    # path('book_home/', include('bookmode.urls')),
]
