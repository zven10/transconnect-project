from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction


class Offre(models.Model):
    PROPOSEE = 'proposee'
    ACCEPTEE = 'acceptee'
    REFUSEE = 'refusee'
    RETIREE = 'retiree'
    STATUT_CHOICES = (
        (PROPOSEE, 'Proposée'),
        (ACCEPTEE, 'Acceptée'),
        (REFUSEE, 'Refusée'),
        (RETIREE, 'Retirée'),
    )

    prix = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), 'Le prix doit être strictement positif.')],
    )
    delai_jours = models.PositiveIntegerField(
        validators=[MinValueValidator(1, "Le délai doit être d'au moins 1 jour.")]
    )
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default=PROPOSEE)
    date_proposition = models.DateField(auto_now_add=True)
    expedition = models.ForeignKey(
        'ExpeditionsApp.Expedition',
        on_delete=models.CASCADE,
        related_name='offres',
    )
    transporteur = models.ForeignKey(
        'EntreprisesApp.Entreprise',
        on_delete=models.CASCADE,
        related_name='offres',
    )
    vehicule = models.ForeignKey(
        'VehiculesApp.Vehicule',
        on_delete=models.PROTECT,
        related_name='offres',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Offre'
        verbose_name_plural = 'Offres'
        ordering = ['-created_at']

    def __str__(self):
        ref = self.expedition.reference if self.expedition_id else '?'
        return f'Offre #{self.pk} — {ref} — {self.prix} TND'

    def clean(self):
        errors = []
        creation = self._state.adding
        transporteur = self.transporteur if self.transporteur_id else None
        vehicule = self.vehicule if self.vehicule_id else None
        expedition = self.expedition if self.expedition_id else None

        # Règle 1 : seule une entreprise transporteur peut proposer une offre
        if transporteur and not transporteur.est_transporteur:
            errors.append("Seule une entreprise de type transporteur peut proposer une offre.")

        # Règle 2 : le véhicule appartient au transporteur de l'offre
        if transporteur and vehicule and vehicule.entreprise_id != transporteur.pk:
            errors.append("Le véhicule doit appartenir à l'entreprise transporteur de l'offre.")

        if creation:
            # Règle 3 : une expédition ne reçoit de nouvelles offres que si elle est publiée
            if expedition and expedition.statut != expedition.PUBLIEE:
                errors.append("Cette expédition n'accepte plus de nouvelles offres (statut ≠ publiée).")
            # Règle 6 : un véhicule indisponible ne peut pas être proposé
            if vehicule and not vehicule.disponible:
                errors.append("Ce véhicule n'est pas disponible.")

        # Règle 4 : pas deux offres « proposee » d'une même entreprise sur la même expédition
        if self.statut == self.PROPOSEE and transporteur and expedition:
            doublon = Offre.objects.filter(
                expedition=expedition, transporteur=transporteur, statut=self.PROPOSEE
            ).exclude(pk=self.pk)
            if doublon.exists():
                errors.append("Cette entreprise a déjà une offre proposée active sur cette expédition.")

        # Règle 7 : gabarit / capacité du véhicule compatibles avec le poids
        if vehicule and expedition and not vehicule.peut_transporter(expedition.poids_kg):
            errors.append(
                f"Véhicule incompatible : {vehicule.get_type_vehicule_display()} "
                f"({vehicule.capacite_kg} kg) pour une expédition de {expedition.poids_kg} kg."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # save() rappelle full_clean() : aucune sauvegarde ORM ne contourne les règles
        self.full_clean()
        ancien_statut = None
        if self.pk:
            ancien_statut = (
                Offre.objects.filter(pk=self.pk).values_list('statut', flat=True).first()
            )
        with transaction.atomic():
            super().save(*args, **kwargs)
            # Règle 5 — cascade à l'acceptation (y compris à la création : ancien_statut=None)
            if self.statut == self.ACCEPTEE and ancien_statut != self.ACCEPTEE:
                self._appliquer_cascade_acceptation()

    def _appliquer_cascade_acceptation(self):
        expedition = self.expedition
        expedition.statut = expedition.ATTRIBUEE
        expedition.save()
        # Boucle + save() (et non .update()) pour déclencher clean()/save() de chaque offre
        autres = Offre.objects.filter(expedition=expedition, statut=self.PROPOSEE).exclude(pk=self.pk)
        for offre in autres:
            offre.statut = self.REFUSEE
            offre.save()
        # Le véhicule retenu est désormais engagé sur cette mission
        if self.vehicule.disponible:
            self.vehicule.disponible = False
            self.vehicule.save()
