from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from EntreprisesApp.models import Entreprise

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


@require_http_methods(['GET', 'POST'])
def supprimer_expedition(request, reference):
    expedition = get_object_or_404(Expedition, reference=reference)
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
        context['transporteurs'] = Entreprise.objects.filter(
            type_entreprise=Entreprise.TYPE_TRANSPORTEUR
        )
        return context


class ExpeditionCreateView(CreateView):
    """L'entreprise chargeur est fixée côté serveur (paramètre d'URL), jamais par le formulaire."""
    model = Expedition
    form_class = ExpeditionForm
    template_name = 'expeditions/form.html'

    def get_entreprise_courante(self):
        return get_object_or_404(
            Entreprise, pk=self.kwargs['entreprise_id'], type_entreprise=Entreprise.TYPE_CHARGEUR
        )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Fixé avant is_valid() : les règles de clean() s'exécutent dans le cycle du formulaire
        form.instance.entreprise = self.get_entreprise_courante()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entreprise'] = self.get_entreprise_courante()
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Expédition publiée.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('expeditions:detail', kwargs={'reference': self.object.reference})


class ExpeditionUpdateView(UpdateView):
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


class ExpeditionDeleteView(DeleteView):
    model = Expedition
    template_name = 'expeditions/confirm_delete.html'
    slug_field = 'reference'
    slug_url_kwarg = 'reference'
    context_object_name = 'expedition'
    success_url = reverse_lazy('expeditions:liste')

    def form_valid(self, form):
        messages.success(self.request, f'Expédition {self.object.reference} supprimée.')
        return super().form_valid(form)
