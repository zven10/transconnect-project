from django.contrib import admin
from django.urls import include, path

from .views import AccueilView

urlpatterns = [
    path('', AccueilView.as_view(), name='accueil'),
    path('admin/', admin.site.urls),
    path('entreprises/', include('EntreprisesApp.urls')),
    path('vehicules/', include('VehiculesApp.urls')),
    path('expeditions/', include('ExpeditionsApp.urls')),
    path('offres/', include('OffresApp.urls')),
]
