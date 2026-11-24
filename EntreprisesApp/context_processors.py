from .mixins import entreprise_de


def entreprise_courante(request):
    """Expose `mon_entreprise` à tous les templates (barre de navigation, boutons d'action).

    Le template ne fait qu'adapter l'affichage : la protection réelle reste dans les vues.
    """
    return {'mon_entreprise': entreprise_de(getattr(request, 'user', None))}
