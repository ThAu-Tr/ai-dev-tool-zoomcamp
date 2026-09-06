from django.urls import path

from . import views

app_name = "household"
urlpatterns = [
    path("", views.home, name="home"),
    path("chores/new/", views.chore_create, name="chore_create"),
    path("chores/<int:pk>/edit/", views.chore_edit, name="chore_edit"),
]
