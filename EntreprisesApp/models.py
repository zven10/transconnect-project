from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Validateurs
# ---------------------------------------------------------------------------

def valider_email_gmail(value):
    """Seuls les emails du domaine gmail.com sont acceptés."""
    if not value or not value.lower().endswith('@gmail.com'):
        raise ValidationError(
            "Seules les adresses e-mail du domaine gmail.com sont acceptées."
        )


# Matricule fiscal tunisien : 7 chiffres + clé + code TVA + catégorie + 3 chiffres,
# séparateurs optionnels (/, -, espace).
MATRICULE_FISCAL_REGEX = (
    r'^\d{7}[/ -]?[A-Za-z][/ -]?[ABDNPEabdnpe][/ -]?[MPCNEmpcne][/ -]?\d{3}$'
)
valider_matricule_fiscal = RegexValidator(
    regex=MATRICULE_FISCAL_REGEX,
    message=(
        "Matricule fiscal invalide. Format attendu : 1234567AAM000 "
        "(ou 1234567/A/A/M/000, 1234567-A-A-M-000)."
    ),
)

valider_telephone = RegexValidator(
    regex=r'^\d{8}$',
    message="Le numéro de téléphone doit comporter exactement 8 chiffres.",
)


# ---------------------------------------------------------------------------
# Utilisateur
# ---------------------------------------------------------------------------

class UtilisateurManager(UserManager):
    """Manager personnalisé : le rôle admin est auto-assigné aux superusers."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', Utilisateur.ROLE_ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class Utilisateur(AbstractUser):
    ROLE_CHARGEUR = 'chargeur'
    ROLE_TRANSPORTEUR = 'transporteur'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = (
        (ROLE_CHARGEUR, 'Chargeur'),
        (ROLE_TRANSPORTEUR, 'Transporteur'),
        (ROLE_ADMIN, 'Administrateur'),
    )

    # PK personnalisée au format AAuserNN (ex. 26user00), remplace l'id d'AbstractUser
    user_id = models.CharField(max_length=8, primary_key=True, editable=False)
    email = models.EmailField(unique=True, validators=[valider_email_gmail])
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CHARGEUR)
    telephone = models.CharField(
        max_length=8, blank=True, validators=[valider_telephone]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UtilisateurManager()

    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @classmethod
    def generer_user_id(cls):
        """AA (année) + 'user' + NN (compteur 00–99 remis à zéro chaque année)."""
        prefixe = f'{timezone.now():%y}user'
        dernier = (
            cls.objects.filter(user_id__startswith=prefixe)
            .order_by('-user_id')
            .values_list('user_id', flat=True)
            .first()
        )
        suivant = int(dernier[-2:]) + 1 if dernier else 0
        if suivant > 99:
            raise ValidationError(
                "Quota annuel atteint : 100 utilisateurs maximum par année (NN = 00–99)."
            )
        return f'{prefixe}{suivant:02d}'

    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = self.generer_user_id()
        if self.is_superuser:
            self.role = self.ROLE_ADMIN
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Entreprise
# ---------------------------------------------------------------------------

class Entreprise(models.Model):
    TYPE_CHARGEUR = 'chargeur'
    TYPE_TRANSPORTEUR = 'transporteur'
    TYPE_CHOICES = (
        (TYPE_CHARGEUR, 'Chargeur'),
        (TYPE_TRANSPORTEUR, 'Transporteur'),
    )

    raison_sociale = models.CharField(max_length=150)
    matricule_fiscal = models.CharField(
        max_length=17, unique=True, validators=[valider_matricule_fiscal]
    )
    type_entreprise = models.CharField(max_length=15, choices=TYPE_CHOICES)
    adresse = models.TextField(
        validators=[MinLengthValidator(20, "L'adresse doit contenir au moins 20 caractères.")]
    )
    # Relation 1—1 : une entreprise est gérée par un compte utilisateur unique
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='entreprise',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entreprise'
        verbose_name_plural = 'Entreprises'
        ordering = ['raison_sociale']

    def __str__(self):
        return f'{self.raison_sociale} ({self.get_type_entreprise_display()})'

    @property
    def est_transporteur(self):
        return self.type_entreprise == self.TYPE_TRANSPORTEUR

    @property
    def est_chargeur(self):
        return self.type_entreprise == self.TYPE_CHARGEUR

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Rôle auto-assigné selon le contexte d'inscription : le compte qui gère
        # l'entreprise prend le rôle correspondant au type de l'entreprise.
        if self.utilisateur_id and not self.utilisateur.is_superuser:
            if self.utilisateur.role != self.type_entreprise:
                self.utilisateur.role = self.type_entreprise
                self.utilisateur.save(update_fields=['role', 'updated_at'])
