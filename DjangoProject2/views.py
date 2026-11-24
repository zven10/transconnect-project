from django.views.generic import TemplateView

from EntreprisesApp.models import Entreprise
from ExpeditionsApp.models import Expedition
from OffresApp.models import Offre
from VehiculesApp.models import Vehicule


class AccueilView(TemplateView):
    template_name = 'accueil.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'expeditions_publiees': Expedition.objects.filter(statut=Expedition.PUBLIEE).count(),
            'offres_proposees': Offre.objects.filter(statut=Offre.PROPOSEE).count(),
            'vehicules_disponibles': Vehicule.objects.filter(disponible=True).count(),
            'entreprises': Entreprise.objects.count(),
        }
        context['dernieres_expeditions'] = (
            Expedition.objects.filter(statut=Expedition.PUBLIEE)
            .select_related('entreprise')[:5]
        )
        return context
