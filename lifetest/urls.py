from django.contrib import admin
from bookmode import views as bookmode_views
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls')),
    path('book_home/', include('bookmode.urls')),
    # path('book_home/', include('bookmode.urls')),
]
