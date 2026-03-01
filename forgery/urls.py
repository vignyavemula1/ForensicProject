from django.urls import path
from . import views

app_name = 'forgery'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('image/', views.upload_view, name='image_upload'),
    path('audio/', views.audio_upload_view, name='audio_upload'),
    path('video/', views.video_upload_view, name='video_upload'),
]
