from django import forms

from .models import Offre


class OffreForm(forms.ModelForm):
    """Création d'une offre : transporteur et statut ne sont JAMAIS exposés (mass assignment)."""

    class Meta:
        model = Offre
        fields = ['expedition', 'vehicule', 'prix', 'delai_jours']


class OffreUpdateForm(forms.ModelForm):
    """Modification : seules les conditions commerciales restent modifiables."""

    class Meta:
        model = Offre
        fields = ['prix', 'delai_jours']
