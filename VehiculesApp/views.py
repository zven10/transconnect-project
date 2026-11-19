from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import VehiculeForm
from .models import Vehicule


# ===========================================================================
# Partie 1 — Function-Based Views (référence)
# ===========================================================================

def liste_vehicules(request):
    vehicules = Vehicule.objects.select_related('entreprise').order_by('immatriculation')
    return render(request, 'vehicules/liste.html', {'vehicules': vehicules})


def detail_vehicule(request, pk):
    vehicule = get_object_or_404(Vehicule.objects.select_related('entreprise'), pk=pk)
    offres = vehicule.offres.select_related('expedition').order_by('-date_proposition')
    return render(request, 'vehicules/detail.html', {'vehicule': vehicule, 'offres': offres})


@require_http_methods(['GET', 'POST'])
def supprimer_vehicule(request, pk):
    vehicule = get_object_or_404(Vehicule, pk=pk)
    if request.method == 'POST':
        vehicule.delete()
        return redirect('vehicules:liste')
    return render(request, 'vehicules/confirm_delete.html', {'vehicule': vehicule})


# ===========================================================================
# Partie 2 — Class-Based Views (routes actives)
# ===========================================================================

class VehiculeListView(ListView):
    model = Vehicule
    template_name = 'vehicules/liste.html'
    context_object_name = 'vehicules'
    paginate_by = 15

    def get_queryset(self):
        return Vehicule.objects.select_related('entreprise').order_by('immatriculation')


class VehiculeDetailView(DetailView):
    model = Vehicule
    template_name = 'vehicules/detail.html'
    context_object_name = 'vehicule'

    def get_queryset(self):
        return Vehicule.objects.select_related('entreprise')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offres'] = self.object.offres.select_related('expedition').order_by('-date_proposition')
        return context


class VehiculeCreateView(CreateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicules/form.html'
    success_url = reverse_lazy('vehicules:liste')

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('entreprise'):
            initial['entreprise'] = self.request.GET['entreprise']
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Véhicule ajouté.')
        return super().form_valid(form)


class VehiculeUpdateView(UpdateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicules/form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Véhicule mis à jour.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('vehicules:detail', kwargs={'pk': self.object.pk})


class VehiculeDeleteView(DeleteView):
    model = Vehicule
    template_name = 'vehicules/confirm_delete.html'
    context_object_name = 'vehicule'
    success_url = reverse_lazy('vehicules:liste')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Suppression impossible : ce véhicule est référencé par des offres.',
            )
            return redirect('vehicules:detail', pk=self.object.pk)
        messages.success(self.request, 'Véhicule supprimé.')
        return response
