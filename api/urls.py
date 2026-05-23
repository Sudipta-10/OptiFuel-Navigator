from django.urls import path
from .views import RouteView, UploadCSVView, UploadStatusView

urlpatterns = [
    path('route/', RouteView.as_view(), name='route'),
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),
    path('upload-status/', UploadStatusView.as_view(), name='upload_status'),
]
