from django import forms

from .models import Entreprise


class EntrepriseForm(forms.ModelForm):
    """utilisateur (compte propriétaire) n'est pas exposé : il se gère via l'admin."""

    class Meta:
        model = Entreprise
        fields = ['raison_sociale', 'matricule_fiscal', 'type_entreprise', 'adresse']
        widgets = {'adresse': forms.Textarea(attrs={'rows': 3})}
