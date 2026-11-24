from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from EntreprisesApp.mixins import ChargeurRequisMixin

from .forms import ExpeditionForm
from .models import Expedition


# ===========================================================================
# Partie 1 — Function-Based Views (conservées comme référence, routes non actives)
# ===========================================================================

def liste_expeditions(request):
    expeditions = (
        Expedition.objects
        .filter(statut=Expedition.PUBLIEE)
        .select_related('entreprise')
        .order_by('-created_at')
    )
    return render(request, 'expeditions/liste.html', {'expeditions': expeditions})


def detail_expedition(request, reference):
    expedition = get_object_or_404(Expedition, reference=reference)
    offres = (
        expedition.offres  # related_name='offres' (sinon : expedition.offre_set)
        .select_related('transporteur', 'vehicule')
        .order_by('-date_proposition')
    )
    return render(request, 'expeditions/detail.html', {'expedition': expedition, 'offres': offres})


@login_required
@require_http_methods(['GET', 'POST'])
def supprimer_expedition(request, reference):
    # Authentification (@login_required) + appartenance (filtre sur l'entreprise du compte)
    expedition = get_object_or_404(
        Expedition, reference=reference, entreprise__utilisateur=request.user
    )
    if request.method == 'POST':
        expedition.delete()
        return redirect('expeditions:liste')
    return render(request, 'expeditions/confirm_delete.html', {'expedition': expedition})


# ===========================================================================
# Partie 2 — Class-Based Views (routes actives)
# ===========================================================================

class ExpeditionListView(ListView):
    model = Expedition
    template_name = 'expeditions/liste.html'
    context_object_name = 'expeditions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Expedition.objects.select_related('entreprise').order_by('-created_at')
        statut = self.request.GET.get('statut', Expedition.PUBLIEE)
        if statut != 'toutes':
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statut_courant'] = self.request.GET.get('statut', Expedition.PUBLIEE)
        context['statuts'] = Expedition.STATUT_CHOICES
        return context


class ExpeditionDetailView(DetailView):
    model = Expedition
    template_name = 'expeditions/detail.html'
    context_object_name = 'expedition'
    slug_field = 'reference'
    slug_url_kwarg = 'reference'

    def get_queryset(self):
        return Expedition.objects.select_related('entreprise')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offres'] = (
            self.object.offres
            .select_related('transporteur', 'vehicule')
            .order_by('-date_proposition', '-created_at')
        )
        return context


class ExpeditionsDeMonEntrepriseMixin:
    """Appartenance : un chargeur ne charge que ses propres expéditions (référence d'un autre → 404)."""

    def get_queryset(self):
        return Expedition.objects.filter(entreprise=self.request.user.entreprise)


class ExpeditionCreateView(ChargeurRequisMixin, CreateView):
    """Plus de paramètre d'URL : l'entreprise chargeur est celle du compte connecté."""
    model = Expedition
    form_class = ExpeditionForm  # entreprise, reference et statut : jamais fournis par le client
    template_name = 'expeditions/form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Fixé avant is_valid() : la règle « entreprise chargeur » de clean() est vérifiée
        # pendant la validation du formulaire (clean() teste entreprise_id avant d'y accéder).
        form.instance.entreprise = self.request.user.entreprise
        return form

    def form_valid(self, form):
        form.instance.entreprise = self.request.user.entreprise
        messages.success(self.request, 'Expédition publiée.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('expeditions:detail', kwargs={'reference': self.object.reference})


class ExpeditionUpdateView(ChargeurRequisMixin, ExpeditionsDeMonEntrepriseMixin, UpdateView):
    model = Expedition
    form_class = ExpeditionForm
    template_name = 'expeditions/form.html'
    slug_field = 'reference'
    slug_url_kwarg = 'reference'

    def form_valid(self, form):
        messages.success(self.request, 'Expédition mise à jour.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('expeditions:detail', kwargs={'reference': self.object.reference})


class ExpeditionDeleteView(ChargeurRequisMixin, ExpeditionsDeMonEntrepriseMixin, DeleteView):
    model = Expedition
    template_name = 'expeditions/confirm_delete.html'
    slug_field = 'reference'
    slug_url_kwarg = 'reference'
    context_object_name = 'expedition'
    success_url = reverse_lazy('expeditions:liste')

    def form_valid(self, form):
        messages.success(self.request, f'Expédition {self.object.reference} supprimée.')
        return super().form_valid(form)
