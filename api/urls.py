from django.urls import path
from .views import RouteView, UploadCSVView

urlpatterns = [
    path('route/', RouteView.as_view(), name='route'),
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),
]
