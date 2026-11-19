from django import forms

from .models import Expedition


class ExpeditionForm(forms.ModelForm):
    """Champs saisis par le chargeur. reference, statut et entreprise ne sont jamais exposés."""

    class Meta:
        model = Expedition
        fields = ['ville_depart', 'ville_arrivee', 'poids_kg', 'date_souhaitee', 'description']
        widgets = {
            'date_souhaitee': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
