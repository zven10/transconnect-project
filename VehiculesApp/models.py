from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Vehicule(models.Model):
    CAMIONNETTE = 'camionnette'
    FOURGON = 'fourgon'
    CAMION_PORTEUR = 'camion_porteur'
    SEMI_REMORQUE = 'semi_remorque'
    TYPE_CHOICES = (
        (CAMIONNETTE, 'Camionnette / utilitaire léger'),
        (FOURGON, 'Fourgon'),
        (CAMION_PORTEUR, 'Camion porteur'),
        (SEMI_REMORQUE, 'Semi-remorque'),
    )
    # Capacité indicative maximale (kg) par gabarit — règle métier 7
    CAPACITE_MAX_PAR_TYPE = {
        CAMIONNETTE: 1_500,
        FOURGON: 3_500,
        CAMION_PORTEUR: 19_000,
        SEMI_REMORQUE: 26_000,
    }

    immatriculation = models.CharField(max_length=20, unique=True)
    type_vehicule = models.CharField(max_length=20, choices=TYPE_CHOICES)
    capacite_kg = models.PositiveIntegerField(
        validators=[MinValueValidator(1, "Une capacité nulle n'est pas acceptée.")]
    )
    disponible = models.BooleanField(default=True)
    entreprise = models.ForeignKey(
        'EntreprisesApp.Entreprise',
        on_delete=models.CASCADE,
        related_name='vehicules',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Véhicule'
        verbose_name_plural = 'Véhicules'
        ordering = ['immatriculation']

    def __str__(self):
        return f'{self.immatriculation} — {self.get_type_vehicule_display()}'

    @property
    def capacite_max_type(self):
        return self.CAPACITE_MAX_PAR_TYPE.get(self.type_vehicule)

    def peut_transporter(self, poids_kg):
        """Règle 7 : le gabarit ET la capacité déclarée doivent couvrir le poids."""
        return poids_kg <= self.capacite_kg and poids_kg <= (self.capacite_max_type or 0)

    def clean(self):
        errors = {}
        # Un véhicule appartient forcément à une entreprise transporteur
        if self.entreprise_id and not self.entreprise.est_transporteur:
            errors['entreprise'] = "Un véhicule doit appartenir à une entreprise de type transporteur."
        # La capacité déclarée doit rester cohérente avec le gabarit
        max_type = self.capacite_max_type
        if self.capacite_kg and max_type and self.capacite_kg > max_type:
            errors['capacite_kg'] = (
                f"Capacité incohérente : un véhicule « {self.get_type_vehicule_display()} » "
                f"est limité à environ {max_type} kg."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
