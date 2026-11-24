"""Mixins de contrôle d'accès réutilisés par toutes les applications (atelier Authentification).

- Authentification (« qui es-tu ? ») : LoginRequiredMixin → visiteur anonyme redirigé vers LOGIN_URL.
- Autorisation par type d'entreprise : UserPassesTestMixin.test_func() → 403 pour un connecté non autorisé.
- Autorisation par appartenance : get_queryset() filtré sur l'entreprise connectée → 404 (section VII).
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def entreprise_de(user):
    """Entreprise gérée par l'utilisateur, ou None (anonyme, ou compte sans entreprise).

    L'accès inverse d'un OneToOneField lève RelatedObjectDoesNotExist (sous-classe
    d'AttributeError) : getattr(..., None) renvoie donc None au lieu d'une exception.
    """
    return getattr(user, 'entreprise', None)


class TransporteurRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vue réservée aux comptes qui gèrent une entreprise de type transporteur."""

    def test_func(self):
        entreprise = entreprise_de(self.request.user)
        return entreprise is not None and entreprise.type_entreprise == 'transporteur'


class ChargeurRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vue réservée aux comptes qui gèrent une entreprise de type chargeur."""

    def test_func(self):
        entreprise = entreprise_de(self.request.user)
        return entreprise is not None and entreprise.type_entreprise == 'chargeur'


class EntrepriseRequiseMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Vue réservée aux comptes qui ont déjà créé leur entreprise (quel que soit son type)."""

    def test_func(self):
        return entreprise_de(self.request.user) is not None
