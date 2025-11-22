from django.contrib import admin
from bookmode import views as bookmode_views
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponse

def health(request):
    return HttpResponse("HELLO WORKING")

urlpatterns = [

    path('health/', health),

    path('admin/', admin.site.urls),
    path('', include('quiz.urls')),
    path('book_home/', include('bookmode.urls')),
    
]
