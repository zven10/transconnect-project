from django import forms

from EntreprisesApp.models import Entreprise

from .models import Vehicule


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        # Liste explicite — jamais '__all__'
        fields = ['immatriculation', 'type_vehicule', 'capacite_kg', 'entreprise', 'disponible']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entreprise'].queryset = Entreprise.objects.filter(
            type_entreprise=Entreprise.TYPE_TRANSPORTEUR
        )
        if self.instance.pk:
            # Un véhicule existant ne change pas de propriétaire depuis le formulaire public
            self.fields['entreprise'].disabled = True
