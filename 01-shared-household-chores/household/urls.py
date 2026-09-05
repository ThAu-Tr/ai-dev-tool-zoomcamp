from django.urls import path

from . import views

app_name = "household"
urlpatterns = [path("", views.home, name="home")]
