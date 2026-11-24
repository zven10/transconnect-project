from django.contrib import admin
from django.urls import include, path

from EntreprisesApp.views import InscriptionView

from .views import AccueilView

urlpatterns = [
    path('', AccueilView.as_view(), name='accueil'),
    path('admin/', admin.site.urls),
    # Authentification : inscription (vue maison) + vues fournies par Django
    # (login, logout, password_change, password_change_done, password_reset…), sans app_name.
    path('comptes/inscription/', InscriptionView.as_view(), name='inscription'),
    path('comptes/', include('django.contrib.auth.urls')),
    path('entreprises/', include('EntreprisesApp.urls')),
    path('vehicules/', include('VehiculesApp.urls')),
    path('expeditions/', include('ExpeditionsApp.urls')),
    path('offres/', include('OffresApp.urls')),
]
