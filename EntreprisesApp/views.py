from django.contrib import messages
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import EntrepriseForm
from .models import Entreprise


# ===========================================================================
# Partie 1 — Function-Based Views (référence)
# ===========================================================================

def liste_entreprises(request):
    entreprises = Entreprise.objects.annotate(nb_vehicules=Count('vehicules', distinct=True))
    return render(request, 'entreprises/liste.html', {'entreprises': entreprises})


def detail_entreprise(request, pk):
    entreprise = get_object_or_404(Entreprise.objects.select_related('utilisateur'), pk=pk)
    return render(request, 'entreprises/detail.html', {'entreprise': entreprise})


@require_http_methods(['GET', 'POST'])
def supprimer_entreprise(request, pk):
    entreprise = get_object_or_404(Entreprise, pk=pk)
    if request.method == 'POST':
        entreprise.delete()
        return redirect('entreprises:liste')
    return render(request, 'entreprises/confirm_delete.html', {'entreprise': entreprise})


# ===========================================================================
# Partie 2 — Class-Based Views (routes actives)
# ===========================================================================

class EntrepriseListView(ListView):
    model = Entreprise
    template_name = 'entreprises/liste.html'
    context_object_name = 'entreprises'
    paginate_by = 15

    def get_queryset(self):
        queryset = Entreprise.objects.annotate(
            nb_vehicules=Count('vehicules', distinct=True),
            nb_expeditions=Count('expeditions', distinct=True),
        ).order_by('raison_sociale')
        type_entreprise = self.request.GET.get('type')
        if type_entreprise:
            queryset = queryset.filter(type_entreprise=type_entreprise)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_courant'] = self.request.GET.get('type', '')
        context['types'] = Entreprise.TYPE_CHOICES
        return context


class EntrepriseDetailView(DetailView):
    model = Entreprise
    template_name = 'entreprises/detail.html'
    context_object_name = 'entreprise'

    def get_queryset(self):
        return Entreprise.objects.select_related('utilisateur')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entreprise = self.object
        context['vehicules'] = entreprise.vehicules.all()
        context['expeditions'] = entreprise.expeditions.order_by('-created_at')
        context['offres'] = entreprise.offres.select_related('expedition', 'vehicule')
        return context


class EntrepriseCreateView(CreateView):
    model = Entreprise
    form_class = EntrepriseForm
    template_name = 'entreprises/form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Entreprise créée.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('entreprises:detail', kwargs={'pk': self.object.pk})


class EntrepriseUpdateView(UpdateView):
    model = Entreprise
    form_class = EntrepriseForm
    template_name = 'entreprises/form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Entreprise mise à jour.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('entreprises:detail', kwargs={'pk': self.object.pk})


class EntrepriseDeleteView(DeleteView):
    model = Entreprise
    template_name = 'entreprises/confirm_delete.html'
    context_object_name = 'entreprise'
    success_url = reverse_lazy('entreprises:liste')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Suppression impossible : des offres référencent les véhicules de cette entreprise.',
            )
            return redirect('entreprises:detail', pk=self.object.pk)
        messages.success(self.request, 'Entreprise supprimée.')
        return response
