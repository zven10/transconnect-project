# AI_LOG — TransConnect

Traçabilité de l'usage de l'IA (workshop PFW 2026-2027). Les commits concernés utilisent les préfixes `AI:` (code généré/assisté) et `Review:` (correction d'un écart, avec renvoi à l'entrée ci-dessous).

---

## Entrée 1 — 20/11/2026 — Bug Hunt du modèle `Offre` (Models part 1, §IV)

- **Outil IA utilisé** : Claude (Claude Code)
- **Prompt** : « Finis le workshop TransConnect à partir des PDF et du code existant. »
- **Sortie obtenue (résumé)** : analyse du premier jet fourni dans le sujet + réécriture du modèle `Offre`.
- **Écarts identifiés vs cahier des charges (4 anomalies)** :
  1. `prix = CharField(max_length=10)` → un prix est un montant : `DecimalField(max_digits=10, decimal_places=2)` + validateur `> 0`. Un `CharField` accepte « abc » et trie les montants comme du texte.
  2. `delai_jours = IntegerField()` → accepte les valeurs négatives : `PositiveIntegerField` + validateur `>= 1`.
  3. `date_proposition = DateField(auto_now=True)` → `auto_now` réécrit la date à **chaque** sauvegarde (acceptation, refus…) : la date de proposition serait perdue. Correct : `auto_now_add=True`.
  4. `vehicule = ForeignKey(..., null=True)` + `save()` vide → le véhicule est obligatoire (une offre est associée à l'un des véhicules du transporteur) et `save()` n'appliquait aucune règle métier. Correct : FK non nulle (`on_delete=PROTECT` pour ne pas perdre l'historique d'une offre), `save()` qui appelle `full_clean()` puis applique la cascade de la règle 5.
- **Correction apportée et justification** : voir `OffresApp/models.py`. Les règles 1 à 7 sont dans `clean()`, la cascade dans `save()` sous `transaction.atomic()`.

## Entrée 2 — 20/11/2026 — Remise à niveau des modèles existants (Models part 1 & 2)

- **Outil IA utilisé** : Claude (Claude Code)
- **Prompt** : idem entrée 1.
- **Écarts identifiés dans le code existant** :
  - Classes `entreprise` / `vehicule` en minuscules (convention PEP 8 : `Entreprise`, `Vehicule`), `def str` au lieu de `__str__` dans `vehicule`.
  - Statuts d'expédition `en cours / termine` au lieu de `publiee / attribuee / en_cours / livree / annulee` (défaut `publiee`).
  - Statuts d'offre avec fautes (`aceptee`, `rentree`) et sans défaut ; champ `date_proposaion` mal orthographié ; `prix` en `FloatField` (erreurs d'arrondi sur des montants).
  - `matricule` (8 caractères) au lieu de `matricule_fiscal` (17 caractères, regex du matricule tunisien) ; `adresse` en `CharField` au lieu de `TextField` (min. 20 caractères).
  - `user_id` aléatoire (`U12345`) au lieu du format `AAuserNN` ; email sans contrainte gmail.com.
  - Référence d'expédition aléatoire (`EXP-12345`) au lieu de `EXP-AA-NNNNN` séquentiel remis à zéro chaque année.
  - Choix de véhicule mal orthographiés (`camionette`, `fougon`), champ `disponibilite` au lieu de `disponible`.
- **Correction apportée** : modèles réécrits, migrations régénérées depuis zéro (les anciennes migrations décrivaient un schéma incompatible : changement de PK, renommage de classes), base `ghassen.sqlite3` recréée puis remplie par `seed_demo`.

## Entrée 3 — 20/11/2026 — Admin (atelier Admin)

- **Écarts identifiés dans `ExpeditionsApp/admin.py` existant** :
  - Imports parasites ajoutés par l'auto-complétion de l'IDE : `fastapi`, `flask.request_started`, `numpy.ma.core.append`, `pyexpat.errors.messages` → plantage au démarrage (modules absents) ; `messages` doit venir de `django.contrib`.
  - `super().queryset.filter(...)` dans le filtre « En retard » (attribut inexistant) ; le filtre doit porter sur `statut='publiee'`.
  - Action : `filter(..., flat=True)` (argument invalide), `c=+1` (affecte +1 au lieu d'incrémenter), `action = [...]` au lieu de `actions`, `message_user(request_started, ...)` au lieu de `request`, double enregistrement (`@admin.register` + `admin.site.register`).
- **Correction** : `ExpeditionAdmin.cloturer_expeditions` — boucle + `full_clean()` + `save()` (jamais `.update()`), ne traite que `en_cours`, messages de succès / avertissement / erreur.
- **Remarque sur l'IA** : pour « une action rapide qui met à jour plusieurs objets », le réflexe d'un assistant est `queryset.update(...)`. Le test `OffresApp.tests.ReglesMetierTests.test_regle5_piege_update` démontre que `.update()` laisse l'expédition en `publiee` et l'autre offre en `proposee`. Le tableau de bord d'intégrité utilise exclusivement `filter/annotate/Exists` (lecture seule).

## Entrée 4 — 20/11/2026 — Views 2 : chasse au mass assignment

- **Prompt de référence (sujet §VI)** : « écris-moi une CreateView Django pour le modèle Offre ».
- **Sortie typique** : `fields = '__all__'` → le formulaire expose `statut` (un transporteur peut créer son offre directement en `acceptee`) et `transporteur` (n'importe qui dépose une offre au nom d'un concurrent).
- **Observation sur notre implémentation** : notre cascade compare au statut précédent en base, qui vaut `None` à la création → **cas B** du sujet : la cascade se déclencherait même à la création. Aucune incohérence de données, mais le processus métier « le chargeur accepte » serait court-circuité : c'est l'exposition du champ qui est le problème.
- **Corrections (2 vues + 2 formulaires)** :
  1. `OffreCreateView` (`OffresApp/views.py`) : `fields = ['expedition', 'vehicule', 'prix', 'delai_jours']`, `transporteur` fixé côté serveur depuis `entreprise_id`, `statut` jamais exposé (défaut `proposee`), menus filtrés (expéditions `publiee`, véhicules disponibles du transporteur). **Amélioration par rapport au sujet** : `transporteur` est affecté dans `get_form()` (avant `is_valid()`), donc les règles 1, 2, 4 s'affichent comme erreurs de formulaire normales ; le `try/except ValidationError` de `form_valid()` reste en filet de sécurité (pas de 500).
  2. `ExpeditionCreateView` : `entreprise` (clé d'appartenance) et `statut` retirés du formulaire, entreprise chargeur fixée depuis l'URL. Test : `ExpeditionsApp.tests.ExpeditionTests.test_creation_entreprise_fixee_cote_serveur` (les champs injectés `entreprise` et `statut=livree` sont ignorés).
  3. `OffreUpdateForm` : seuls `prix` et `delai_jours` sont modifiables, et uniquement tant que l'offre est `proposee`.
  4. `VehiculeForm` : `entreprise` limité aux transporteurs et désactivé en modification (pas de transfert d'un véhicule vers un autre propriétaire).
- **Ce que cela apprend sur l'outil** : l'assistant optimise pour « ça marche visuellement » ; les champs sensibles (statut, clé d'appartenance, dates auto) doivent être listés explicitement et fixés côté serveur — c'est au développeur de relire.

## Entrée 5 — 24/11/2026 — Authentification (connexion, inscription, protection des vues)

- **Outil IA utilisé** : Claude (Claude Code)
- **Prompt** : « Réalise la partie Authentification du workshop à partir du PDF. »
- **Écarts relevés et corrigés pendant la revue** :
  1. **Ordre MRO et `dispatch()`** : `OffreUpdateView` surchargeait `dispatch()` pour refuser une offre non « proposée ». Une fois `TransporteurRequisMixin` ajouté, ce `dispatch()` de la classe s'exécutait **avant** celui du mixin (Python lit la classe elle-même avant ses parents) : l'objet était chargé avant le contrôle d'accès, et `request.user.entreprise` levait une exception pour un anonyme. Le contrôle de statut est déplacé dans `get()` / `post()`.
  2. **Templates de changement de mot de passe** : `django.contrib.admin` fournit déjà `registration/password_change_form.html` ; `EntreprisesApp` est placée avant l'admin dans `INSTALLED_APPS` pour que nos templates soient trouvés en premier (test `test_changement_mot_de_passe_template_du_projet`).
  3. **`accepter_offre`** : le sujet ne demande que la connexion, mais un transporteur connecté pouvait alors accepter une offre sur l'expédition d'un chargeur. L'offre est désormais cherchée avec `expedition__entreprise__utilisateur=request.user` (404 sinon). Même principe pour `retirer_offre` et les FBV de suppression conservées en référence.
  4. **Code mort** : la vue d'aiguillage `proposer_offre` (choix du transporteur dans une liste, partie Views 2) n'a plus de raison d'être et est supprimée avec sa route ; le lien « Proposer une offre » pointe vers `offres:ajouter?expedition=<pk>`.
- **Vérifications** : 61 tests (dont `VehiculeTests.test_section_VII_vehicule_d_un_autre_transporteur`, `ExpeditionTests.test_suppression_anonyme_redirige_avec_next`, `InscriptionTests.test_champs_sensibles_ignores`) ; manipulation de la section VII rejouée dans le navigateur (`transsahel.demo` : 200 sur ses véhicules, 404 sur celui de `capbon.demo`).
