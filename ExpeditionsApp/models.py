from EntreprisesApp import models
from django.db import models
# Create your models here.
class Expedition(models.Model):
    reference=models.CharField(unique=True, auto_created=True,)
    ville_depart=models.CharField(max_length=100)
    ville_arrivee=models.CharField(max_length=100)
    date_shouhaitee=models.DateField()
    description=models.TextField()
    statut=models.CharField(max_length=15,choices=(('en cours','en cours'),('termine','termine')))
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    entreprise=models.ForeignKey('EntreprisesApp.entreprise',on_delete=models.CASCADE,related_name='expeditions')
def __str__(self):
    return f"Expedition {self.reference} -{self.ville_depart} -> {self.ville_arrivee} - {self.date_shouhaitee} - {self.statut} - {self.entreprise} "