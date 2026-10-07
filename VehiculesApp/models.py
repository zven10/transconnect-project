from django.db import models
import EntreprisesApp
class vehicule(models.Model):
    immatriculation=models.CharField(max_length=8,unique=True)
    capacite_kg=models.PositiveIntegerField()
    type_vehicule=models.CharField(max_length=15,choices=(('camionette','camionette'),('fougon','fougon'),('camion_porteur','camion_porteur'),
    ('semi_remorque','semi_remorque')))
    disponibilite=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    entreprise=models.ForeignKey('EntreprisesApp.entreprise',
        on_delete=models.CASCADE,
        related_name='vehicules',
    )
    def str(self):
        return self.immatriculation
# Create your models here.
