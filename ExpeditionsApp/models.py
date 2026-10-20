import random
import string
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Expedition(models.Model):
  STATUT_CHOICES = (
      ('en cours', 'En cours'),
      ('termine', 'Terminé'),
  )

  reference = models.CharField(
      max_length=20, unique=True, editable=False, blank=True
  )
  ville_depart = models.CharField(max_length=100)
  ville_arrivee = models.CharField(max_length=100)
  date_souhaitee = models.DateField()
  description = models.TextField()
  poids_kg = models.DecimalField(
      max_digits=8, decimal_places=2, default=0.00, help_text='Poids en kg'
  )
  statut = models.CharField(
      max_length=15, choices=STATUT_CHOICES, default='en cours'
  )

  entreprise = models.ForeignKey(
      'EntreprisesApp.entreprise',
      on_delete=models.CASCADE,
      related_name='expeditions',
  )

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    verbose_name = 'Expédition'
    verbose_name_plural = 'Expéditions'
    ordering = ['-created_at']

  def __str__(self):
    return f'Expédition {self.reference} ({self.ville_depart} -> {self.ville_arrivee})'


# --- SIGNAL POUR GÉNÉRATION AUTOMATIQUE DE LA RÉFÉRENCE ---
@receiver(pre_save, sender=Expedition)
def generate_expedition_reference(sender, instance, **kwargs):
  if not instance.reference:
    while True:
      random_digits = ''.join(random.choices(string.digits, k=5))
      new_ref = f'EXP-{random_digits}'
      if not Expedition.objects.filter(reference=new_ref).exists():
        instance.reference = new_ref
        break
