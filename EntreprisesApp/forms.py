from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Entreprise, Utilisateur


class InscriptionForm(UserCreationForm):
    """Inscription publique.

    password1 / password2 (saisie en double, validation, hachage) viennent de UserCreationForm.
    role, is_staff et is_superuser ne sont JAMAIS exposés : un visiteur ne doit pas pouvoir
    se donner des droits (même raisonnement que fields = '__all__' en Views 2).
    Les validateurs du modèle s'appliquent tels quels : email @gmail.com, téléphone à 8 chiffres ;
    user_id est généré par Utilisateur.save() au format AAuserNN.
    """

    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = ('username', 'email', 'telephone')


class EntrepriseForm(forms.ModelForm):
    """utilisateur (compte propriétaire) n'est jamais exposé : il est fixé depuis request.user."""

    class Meta:
        model = Entreprise
        fields = ['raison_sociale', 'matricule_fiscal', 'type_entreprise', 'adresse']
        widgets = {'adresse': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Changer de type casserait les règles (véhicules d'un transporteur, expéditions d'un chargeur)
            self.fields['type_entreprise'].disabled = True
