from django.urls import path

from . import views

app_name = "household"
urlpatterns = [
    path("", views.home, name="home"),
    path("chores/new/", views.chore_create, name="chore_create"),
    path("chores/<int:pk>/edit/", views.chore_edit, name="chore_edit"),
    path("chores/<int:pk>/delete/", views.chore_delete, name="chore_delete"),
    path("chores/<int:pk>/complete/", views.chore_complete, name="chore_complete"),
    path("members/<int:pk>/", views.member_detail, name="member_detail"),
]
