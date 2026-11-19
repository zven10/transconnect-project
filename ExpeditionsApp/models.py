from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Expedition(models.Model):
    PUBLIEE = 'publiee'
    ATTRIBUEE = 'attribuee'
    EN_COURS = 'en_cours'
    LIVREE = 'livree'
    ANNULEE = 'annulee'
    STATUT_CHOICES = (
        (PUBLIEE, 'Publiée'),
        (ATTRIBUEE, 'Attribuée'),
        (EN_COURS, 'En cours'),
        (LIVREE, 'Livrée'),
        (ANNULEE, 'Annulée'),
    )

    # Format EXP-AA-NNNNN, généré automatiquement dans save()
    reference = models.CharField(max_length=12, unique=True, editable=False)
    ville_depart = models.CharField(max_length=100)
    ville_arrivee = models.CharField(max_length=100)
    poids_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), "Le poids doit être strictement positif.")],
        help_text='Poids en kg',
    )
    date_souhaitee = models.DateField()
    description = models.TextField(blank=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default=PUBLIEE)
    entreprise = models.ForeignKey(
        'EntreprisesApp.Entreprise',
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
        return f'{self.reference} ({self.ville_depart} → {self.ville_arrivee})'

    @classmethod
    def generer_reference(cls):
        """EXP-AA-NNNNN : compteur 00001–99999 remis à zéro chaque année."""
        prefixe = f'EXP-{timezone.now():%y}-'
        derniere = (
            cls.objects.filter(reference__startswith=prefixe)
            .order_by('-reference')
            .values_list('reference', flat=True)
            .first()
        )
        suivant = int(derniere[-5:]) + 1 if derniere else 1
        if suivant > 99_999:
            raise ValidationError("Quota annuel de références d'expédition atteint (99999).")
        return f'{prefixe}{suivant:05d}'

    def clean(self):
        if self.entreprise_id and not self.entreprise.est_chargeur:
            raise ValidationError(
                {'entreprise': "Une expédition doit être publiée par une entreprise de type chargeur."}
            )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generer_reference()
        self.full_clean()
        ancien_statut = None
        if self.pk:
            ancien_statut = (
                Expedition.objects.filter(pk=self.pk).values_list('statut', flat=True).first()
            )
        super().save(*args, **kwargs)
        # Fin de mission : les véhicules affectés redeviennent disponibles
        if self.statut in (self.LIVREE, self.ANNULEE) and ancien_statut != self.statut:
            for offre in self.offres.filter(statut='acceptee').select_related('vehicule'):
                if not offre.vehicule.disponible:
                    offre.vehicule.disponible = True
                    offre.vehicule.save()
