from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from EntreprisesApp.mixins import TransporteurRequisMixin
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


@login_required
@require_http_methods(['GET', 'POST'])
def supprimer_offre(request, pk):
    offre = get_object_or_404(Offre, pk=pk, transporteur__utilisateur=request.user)
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


class OffresDeMonEntrepriseMixin:
    """Appartenance : un transporteur ne charge que ses propres offres (pk d'une autre → 404)."""

    def get_queryset(self):
        return Offre.objects.filter(transporteur=self.request.user.entreprise).select_related('expedition')


class OffreCreateView(TransporteurRequisMixin, CreateView):
    """Atelier Authentification : plus de entreprise_id dans l'URL, le transporteur est
    l'entreprise du compte connecté. get_form(), form_valid() et get_success_url() sont
    inchangés par rapport à la partie Views 2."""
    model = Offre
    form_class = OffreForm  # ['expedition', 'vehicule', 'prix', 'delai_jours']
    template_name = 'offres/form.html'

    def get_entreprise_courante(self):
        return self.request.user.entreprise

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


class OffreUpdateView(TransporteurRequisMixin, OffresDeMonEntrepriseMixin, UpdateView):
    model = Offre
    form_class = OffreUpdateForm
    template_name = 'offres/form.html'

    # Le contrôle de statut est fait dans get()/post() et non dans dispatch() : dispatch()
    # de cette classe passerait AVANT celui du mixin (ordre MRO) et chargerait l'objet
    # avant que l'accès n'ait été vérifié.
    def _refuser_si_non_modifiable(self):
        self.object = self.get_object()
        if self.object.statut != Offre.PROPOSEE:
            messages.error(self.request, 'Seule une offre au statut « proposée » peut être modifiée.')
            return redirect('offres:detail', pk=self.object.pk)
        return None

    def get(self, request, *args, **kwargs):
        return self._refuser_si_non_modifiable() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._refuser_si_non_modifiable() or super().post(request, *args, **kwargs)

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


class OffreDeleteView(TransporteurRequisMixin, OffresDeMonEntrepriseMixin, DeleteView):
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


@login_required
@require_POST
def accepter_offre(request, pk):
    """Le chargeur propriétaire de l'expédition accepte une offre : save() déclenche la cascade
    de la règle 5. Une offre sur l'expédition d'un autre chargeur est introuvable (404)."""
    offre = get_object_or_404(
        Offre.objects.select_related('expedition'),
        pk=pk, expedition__entreprise__utilisateur=request.user,
    )
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


@login_required
@require_POST
def retirer_offre(request, pk):
    """Le transporteur retire SON offre (proposee → retiree)."""
    offre = get_object_or_404(Offre, pk=pk, transporteur__utilisateur=request.user)
    if offre.statut == Offre.PROPOSEE:
        offre.statut = Offre.RETIREE
        offre.save()
        messages.success(request, f'Offre #{offre.pk} retirée.')
    else:
        messages.error(request, 'Seule une offre « proposée » peut être retirée.')
    return redirect('offres:detail', pk=offre.pk)
