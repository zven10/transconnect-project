import random
import string
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Utilisateur(AbstractUser):
  user_id = models.CharField(
      max_length=8, primary_key=True, editable=False, unique=True
  )
  email = models.EmailField(unique=True)
  role = models.CharField(
      max_length=20,
      choices=(
          ('chargeur', 'chargeur'),
          ('transporteur', 'transporteur'),
          ('admin', 'admin'),
      ),
      default='chargeur',
  )
  telephone = models.CharField(max_length=8, blank=True, null=True)
  username = models.CharField(max_length=100, unique=True)

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  def __str__(self):
    return f'{self.username} ({self.role})'


class entreprise(models.Model):
  raison_sociale = models.CharField(max_length=100)
  matricule = models.CharField(max_length=8, unique=True)
  type_entreprise = models.CharField(
      max_length=15,
      choices=(
          ('chargeur', 'chargeur'),
          ('transporteur', 'transporteur'),
      ),
  )
  adresse = models.CharField(max_length=100)

  # null=True et blank=True permettent de créer une entreprise sans utilisateur obligatoire dès le départ
  utilisateur = models.OneToOneField(
      Utilisateur,
      on_delete=models.CASCADE,
      related_name='entreprise',
      blank=True,
      null=True,
  )

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  def __str__(self):
    return self.raison_sociale


# --- SIGNAL POUR LA GÉNÉRATION AUTOMATIQUE DU user_id ---
@receiver(pre_save, sender=Utilisateur)
def generate_user_id(sender, instance, **kwargs):
  if not instance.user_id:
    while True:
      random_digits = ''.join(random.choices(string.digits, k=5))
      new_id = f'U{random_digits}'
      if not Utilisateur.objects.filter(user_id=new_id).exists():
        instance.user_id = new_id
        break