from django.urls import include, path

urlpatterns = [path("", include("household.urls"))]
