from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from EntreprisesApp.models import Entreprise
from ExpeditionsApp.models import Expedition
from VehiculesApp.models import Vehicule

from .forms import OffreForm, OffreUpdateForm
from .models import Offre


# ===========================================================================
# Partie 1 — Function-Based Views (référence)
# ===========================================================================

def liste_offres(request):
    offres = Offre.objects.select_related('expedition', 'transporteur', 'vehicule')
    return render(request, 'offres/liste.html', {'offres': offres})


def detail_offre(request, pk):
    offre = get_object_or_404(
        Offre.objects.select_related('expedition', 'transporteur', 'vehicule'), pk=pk
    )
    return render(request, 'offres/detail.html', {'offre': offre})


@require_http_methods(['GET', 'POST'])
def supprimer_offre(request, pk):
    offre = get_object_or_404(Offre, pk=pk)
    if request.method == 'POST':
        offre.delete()
        return redirect('offres:liste')
    return render(request, 'offres/confirm_delete.html', {'offre': offre})


# ===========================================================================
# Partie 2 — Class-Based Views (routes actives)
# ===========================================================================

class OffreListView(ListView):
    model = Offre
    template_name = 'offres/liste.html'
    context_object_name = 'offres'
    paginate_by = 15

    def get_queryset(self):
        queryset = Offre.objects.select_related('expedition', 'transporteur', 'vehicule')
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = Offre.STATUT_CHOICES
        context['statut_courant'] = self.request.GET.get('statut', '')
        return context


class OffreDetailView(DetailView):
    model = Offre
    template_name = 'offres/detail.html'
    context_object_name = 'offre'

    def get_queryset(self):
        return Offre.objects.select_related('expedition', 'transporteur', 'vehicule')


class OffreCreateView(CreateView):
    """Version corrigée (atelier Views 2, §VI) — ni statut ni transporteur exposés."""
    model = Offre
    form_class = OffreForm
    template_name = 'offres/form.html'

    def get_entreprise_courante(self):
        # Pas d'authentification à ce stade : l'entreprise est passée via l'URL.
        if not hasattr(self, '_entreprise'):
            self._entreprise = get_object_or_404(
                Entreprise, pk=self.kwargs['entreprise_id'],
                type_entreprise=Entreprise.TYPE_TRANSPORTEUR,
            )
        return self._entreprise

    def get_initial(self):
        initial = super().get_initial()
        expedition_id = self.request.GET.get('expedition')
        if expedition_id:
            initial['expedition'] = expedition_id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        entreprise = self.get_entreprise_courante()
        # Ne proposer que les expéditions encore ouvertes aux offres
        form.fields['expedition'].queryset = Expedition.objects.filter(statut=Expedition.PUBLIEE)
        # Ne proposer que les véhicules disponibles de l'entreprise courante
        form.fields['vehicule'].queryset = Vehicule.objects.filter(entreprise=entreprise, disponible=True)
        # transporteur fixé AVANT is_valid() → les règles 1, 2, 4 s'exécutent pendant la validation
        form.instance.transporteur = entreprise
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entreprise'] = self.get_entreprise_courante()
        return context

    def form_valid(self, form):
        # transporteur : déterminé par le contexte, jamais fourni par le client
        form.instance.transporteur = self.get_entreprise_courante()
        # statut : jamais exposé, toujours la valeur par défaut ('proposee')
        try:
            response = super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e.messages)
            return self.form_invalid(form)
        messages.success(self.request, 'Offre envoyée.')
        return response

    def get_success_url(self):
        return reverse('expeditions:detail', kwargs={'reference': self.object.expedition.reference})


class OffreUpdateView(UpdateView):
    model = Offre
    form_class = OffreUpdateForm
    template_name = 'offres/form.html'

    def dispatch(self, request, *args, **kwargs):
        offre = self.get_object()
        if offre.statut != Offre.PROPOSEE:
            messages.error(request, 'Seule une offre au statut « proposée » peut être modifiée.')
            return redirect('offres:detail', pk=offre.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e.messages)
            return self.form_invalid(form)
        messages.success(self.request, 'Offre mise à jour.')
        return response

    def get_success_url(self):
        return reverse('offres:detail', kwargs={'pk': self.object.pk})


class OffreDeleteView(DeleteView):
    model = Offre
    template_name = 'offres/confirm_delete.html'
    context_object_name = 'offre'
    success_url = reverse_lazy('offres:liste')

    def form_valid(self, form):
        if self.object.statut == Offre.ACCEPTEE:
            messages.error(self.request, 'Une offre acceptée ne peut pas être supprimée.')
            return redirect('offres:detail', pk=self.object.pk)
        messages.success(self.request, 'Offre supprimée.')
        return super().form_valid(form)


@require_POST
def accepter_offre(request, pk):
    """Le chargeur accepte une offre : save() déclenche la cascade de la règle 5."""
    offre = get_object_or_404(Offre.objects.select_related('expedition'), pk=pk)
    if offre.statut != Offre.PROPOSEE or offre.expedition.statut != Expedition.PUBLIEE:
        messages.error(request, "Cette offre ne peut plus être acceptée.")
    else:
        offre.statut = Offre.ACCEPTEE
        try:
            offre.save()  # full_clean() + cascade (pas de .update())
            messages.success(
                request,
                f'Offre #{offre.pk} acceptée : expédition attribuée, autres offres refusées.',
            )
        except ValidationError as e:
            messages.error(request, ' '.join(e.messages))
    return redirect('expeditions:detail', reference=offre.expedition.reference)


@require_POST
def retirer_offre(request, pk):
    """Le transporteur retire son offre (proposee → retiree)."""
    offre = get_object_or_404(Offre, pk=pk)
    if offre.statut == Offre.PROPOSEE:
        offre.statut = Offre.RETIREE
        offre.save()
        messages.success(request, f'Offre #{offre.pk} retirée.')
    else:
        messages.error(request, 'Seule une offre « proposée » peut être retirée.')
    return redirect('offres:detail', pk=offre.pk)


@require_GET
def proposer_offre(request):
    """Aiguillage depuis la page d'une expédition : choisit le transporteur puis redirige."""
    entreprise = get_object_or_404(
        Entreprise, pk=request.GET.get('entreprise_id') or 0,
        type_entreprise=Entreprise.TYPE_TRANSPORTEUR,
    )
    url = reverse('offres:ajouter', kwargs={'entreprise_id': entreprise.pk})
    expedition = request.GET.get('expedition')
    if expedition and expedition.isdigit():
        url += f'?expedition={expedition}'
    return redirect(url)
