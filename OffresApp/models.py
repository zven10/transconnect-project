from django.db import models
class Offre(models.Model):
    prix=models.FloatField()
    date_proposaion=models.DateField(auto_now_add=True)
    delai_jours=models.PositiveIntegerField()
    statut=models.CharField(max_length=15,choices=(('proposee','proposee'),('aceptee','aceptee'),('refusee','refusee'),('rentree','rentree')))
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    vehicule=models.ForeignKey('VehiculesApp.vehicule',on_delete=models.CASCADE,related_name='offres')
    expedition=models.ForeignKey('ExpeditionsApp.Expedition',on_delete=models.CASCADE,related_name='offres')
    transporteur=models.ForeignKey('EntreprisesApp.entreprise',on_delete=models.CASCADE,related_name='offres')
# Create your models here.
