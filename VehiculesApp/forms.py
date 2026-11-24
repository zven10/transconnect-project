from django import forms

from .models import Vehicule


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        # Liste explicite — jamais '__all__'.
        # entreprise : retirée du formulaire (atelier Authentification, travail individuel) ;
        # elle est fixée côté serveur depuis request.user.entreprise dans VehiculeCreateView.
        fields = ['immatriculation', 'type_vehicule', 'capacite_kg', 'disponible']
