# TransConnect — Workshop Python Framework for the Web (2026-2027)

Plateforme de mise en relation chargeurs / transporteurs (Django 5.2).

| App | Modèles | Pages publiques |
|---|---|---|
| `EntreprisesApp` | `Utilisateur` (AbstractUser), `Entreprise` | `/entreprises/` |
| `VehiculesApp` | `Vehicule` | `/vehicules/` |
| `ExpeditionsApp` | `Expedition` | `/expeditions/` |
| `OffresApp` | `Offre` | `/offres/` |

## Lancer le projet

```powershell
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- Site public : http://127.0.0.1:8000/
- Admin : http://127.0.0.1:8000/admin/ — tableau de bord d'intégrité : http://127.0.0.1:8000/admin/health-check/
- Tests : `uv run python manage.py test` (35 tests : règles métier, vues, action admin, health-check)

Base de données : `ghassen.sqlite3` (nom de l'étudiant). Les comptes créés par `seed_demo` ont le mot de passe `demo12345`.

## Partie Models

- **Utilisateur** : PK `user_id` au format `AAuserNN` (ex. `26user00`, compteur 00–99 par année), email `@gmail.com` uniquement, rôle `chargeur / transporteur / admin` auto-assigné (superuser → admin ; compte rattaché à une entreprise → type de l'entreprise). `AUTH_USER_MODEL = 'EntreprisesApp.Utilisateur'`.
- **Entreprise** : `matricule_fiscal` validé par la regex du matricule tunisien, `adresse` ≥ 20 caractères, OneToOne vers `Utilisateur`.
- **Vehicule** : capacité > 0, entreprise transporteur obligatoire, capacité cohérente avec le gabarit.
- **Expedition** : référence `EXP-AA-NNNNN` séquentielle, poids > 0, entreprise chargeur obligatoire, statut par défaut `publiee`.
- **Offre** : prix > 0, délai ≥ 1, `date_proposition` en `auto_now_add`.

Règles métier (`clean()` + `save()` qui rappelle `full_clean()`), toutes testées :

1. Seul un transporteur propose une offre.
2. Le véhicule appartient au transporteur de l'offre.
3. Nouvelles offres uniquement sur une expédition `publiee`.
4. Pas deux offres `proposee` d'une même entreprise sur la même expédition.
5. Acceptation → expédition `attribuee`, autres offres `proposee` → `refusee`, véhicule retenu indisponible (le véhicule redevient disponible quand l'expédition est `livree`/`annulee`).
6. Véhicule indisponible interdit sur une nouvelle offre.
7. Gabarit / capacité compatibles avec le poids (camionnette 1,5 t · fourgon 3,5 t · porteur 19 t · semi 26 t).

## Partie Admin

ModelAdmin pour les 5 modèles (list_display, list_filter, search_fields, list_editable, ordering, date_hierarchy, list_per_page, fieldsets, readonly_fields, autocomplete_fields), badges de statut colorés (Expedition et Offre), `VehiculeInline` (Tabular, éditable) dans Entreprise, `OffreInline` (Stacked, lecture seule, `show_change_link`) dans Expedition, filtre « En retard », lecture seule dynamique d'une offre acceptée, actions « Clôturer les expéditions sélectionnées » et « Exporter en CSV », branding TransConnect (`TransConnectAdminSite`, `templates/admin/base_site.html`).

### Tableau de bord d'intégrité (`/admin/health-check/`)

Vue enregistrée par surcharge de `get_urls()` sur `TransConnectAdminSite` (`DjangoProject2/admin_site.py`), requêtes ORM uniquement (`filter`, `annotate`, `Count`, `Exists`).

| Contrôle | Règle protégée | Scénario réaliste d'apparition |
|---|---|---|
| Offres orphelines | 3, 5 | Expédition annulée/livrée via `Expedition.objects.filter(...).update(statut=...)` : les offres actives ne sont pas refusées. |
| Expéditions bloquées (> 7 j en `publiee`) | suivi opérationnel | Aucune offre acceptée, ou acceptation faite par `.update()` sans changer l'expédition. |
| Transporteurs sans flotte | 2, 6 | Import en masse d'entreprises (`bulk_create`) sans leurs véhicules, ou suppression de la flotte. |
| Incohérence de disponibilité | 5, 6 | Offre acceptée par `.update()` : le véhicule reste `disponible=True` et peut être proposé ailleurs. |
| Doublons de proposition | 4 | `bulk_create` d'offres ou `.update(statut='proposee')` pour « réactiver » des offres retirées. |
| Offre acceptée sur expédition non attribuée | 5 | Exactement la manipulation de l'atelier Admin §VII : `Offre.objects.filter(pk=…).update(statut='acceptee')`. |

Résultat sur les données du seed : aucune anomalie (toutes les écritures passent par `save()`). Après la manipulation du §VII (`.update()` sur une offre de `EXP-26-00001`), les contrôles « Offre acceptée sur expédition non attribuée » et « Incohérence de disponibilité » remontent `EXP-26-00001` — vérifié par `OffresApp.tests.HealthCheckTests`.

## Parties Views 1 & 2

- `urls.py` par application avec `app_name` et routes nommées, inclus depuis `DjangoProject2/urls.py`.
- FBV de la partie 1 (liste / détail / suppression protégée) conservées dans chaque `views.py` comme référence ; les routes actives pointent vers les CBV équivalentes, avec les **mêmes noms** (`liste`, `detail`, `supprimer`).
- CRUD complet en CBV (`ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`) pour Entreprise, Véhicule, Expédition et Offre, avec un `ModelForm` par entité listant explicitement ses champs.
- `base.html` avec barre de navigation et messages ; templates utilisant `{% empty %}` et les filtres `date`, `default`, `floatformat`, `truncatewords`, `pluralize`, `yesno`, `upper`, `title`, `timesince`, `linebreaksbr`, `default_if_none`, `truncatechars`, `length`.
- Actions qui modifient des données uniquement en POST avec `{% csrf_token %}` (suppression, acceptation, retrait d'offre) ; pattern Post/Redirect/Get.
- Parcours complet : fiche expédition → « Proposer une offre » (choix du transporteur) → formulaire filtré → retour sur l'expédition → « Accepter » (POST → cascade règle 5).

### Comparaison FBV / CBV

| | FBV (`liste_vehicules`, `detail_vehicule`, `supprimer_vehicule`) | CBV (`VehiculeListView`, `VehiculeDetailView`, `VehiculeDeleteView`) |
|---|---|---|
| Lignes | ~17 lignes pour les 3 vues | ~25 lignes, mais pagination, gestion GET/POST et 404 inclus |
| Lisibilité | tout est visible dans la fonction | le comportement par défaut est hérité, il faut connaître la classe parente |
| Personnalisation | naturelle pour une logique non-CRUD (`accepter_offre`, `proposer_offre` restent en FBV) | points d'extension ciblés : `get_queryset`, `get_context_data`, `get_form`, `form_valid`, `get_success_url` |
| Création / modification | demanderait de réécrire le cycle `is_valid` + PRG à la main | `CreateView` / `UpdateView` + `success_url` gèrent le PRG nativement |

La chasse au mass assignment est documentée dans `AI_LOG.md` (entrée 4).
