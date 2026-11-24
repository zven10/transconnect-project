from django.urls import path

from . import views

app_name = 'expeditions'

# Routes CBV actives (mêmes noms que les routes FBV de la partie 1).
# 'ajouter/...' est déclaré avant '<str:reference>/' pour ne pas être intercepté.
urlpatterns = [
    path('', views.ExpeditionListView.as_view(), name='liste'),
    path('ajouter/', views.ExpeditionCreateView.as_view(), name='ajouter'),
    path('<str:reference>/', views.ExpeditionDetailView.as_view(), name='detail'),
    path('<str:reference>/modifier/', views.ExpeditionUpdateView.as_view(), name='modifier'),
    path('<str:reference>/supprimer/', views.ExpeditionDeleteView.as_view(), name='supprimer'),
]
