from django.db import models
from  django.contrib.auth.models import AbstractUser
# Create your models here.
class Utilisateur(AbstractUser):
    user_id=models.CharField(max_length=8,primary_key=True,editable=False)
    email=models.EmailField(unique=True)
    role=models.CharField(max_length=20,choices=(('chargeur','chargeur'),('transpoerteur','transporteur'),('admin','admin')),default='chargeur')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    telephone=models.CharField(max_length=8,blank=True,null=True)

class entreprise(models.Model):
    raison_sociale=models.CharField(max_length=100)
    matricule=models.CharField(max_length=8,unique=True)
    type_entreprise=models.CharField(max_length=15,choices=(('charguer','charguer'),('transporteur','transporteur')))
    adresse=models.CharField(max_length=100)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    utilisateur=models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='entreprise',
    )

