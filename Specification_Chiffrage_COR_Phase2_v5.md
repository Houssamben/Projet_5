# Spécification de reconstruction — `Chiffrage_COR_Phase2_v5.xlsx`

> **Objectif** : reconstruire à l'identique le classeur Excel de chiffrage du projet COR Phase 2 (v5). Ce document contient **toutes les données, formules, mises en forme et règles** nécessaires. Ne pas inventer de valeurs : utiliser uniquement celles listées ici.

## 1. Contexte (pour comprendre, pas à recopier)

- Projet Dataiku **COR Phase 2** (Collection & Recovery, prélèvements BPLS, 7 pays SIELE : BE DE ES FR GB IT NL), 2 data products : `DIRECT_DEBITS_CASH_FLOW_DETAILS` et `DIRECT_DEBITS_CASH_FLOW_KPI` (PostgreSQL, lus par Power BI).
- Source : photos mensuelles DCP (COS, CSV, 7 tables). Mécanisme retenu : chaque mois, la photo M recalcule et **remplace** les mois d'émission M-5 → M (« Annule & Remplace »), mois plus anciens figés.
- Organisation Dataiku héritée de la phase 1 : 3 projets `01_COR_DATASET` → `02_COR_DESIGN` → `03_COR_PRODUCT` (équivalents bronze / silver / gold).
- Ce chiffrage v5 remplace un chiffrage v4 (« Option C », 85,5 j). Contrainte : **ne pas dépasser 2,5 mois** → total v5 = 52,5 j.

## 2. Règles générales du classeur

| Élément | Règle |
|---|---|
| Bibliothèque conseillée | Python `openpyxl` |
| Police | Calibri partout |
| Bordures | fines (`thin`), couleur `BFBFBF`, sur toutes les cellules de tableau |
| Alignement | vertical centré ; horizontal selon les colonnes indiquées |
| Couleurs (hex) | Bleu nuit `1F3864` (titres, en-têtes, total) · Bleu `2E75B6` (lignes de lot) · Bleu foncé `154360` (ligne des dates du planning) · Data Engineer `BDD7EE` · MLOps `E2EFDA` · Cycles de test `FFF9C4` (texte activité `8B4513`) · Sous-total `D9D9D9` · Lots transverses (9-11) en synthèse `F2F2F2` · Sous-titre `D9E1F2` · Saisie/hypothèse `FFFF00` · Orange titre cycles `C55A11` · Lignes alternées cycles `FCE4D6`/`FFFFFF` · Risques `FFF2CC` |
| Texte des valeurs saisies | police bleue `0000FF` (charges des tâches, semaines début/fin, paramètres) |
| Formules | **obligatoires** pour sous-totaux, totaux, %, liens entre onglets (ne jamais écrire un résultat calculé en dur) |
| Propriétés du fichier | auteur = « Équipe projet COR » ; aucune mention d'outil ou d'IA |
| Ordre des onglets | 1. Synthèse · 2. Détail charges · 3. Planning · 4. Écarts vs v4 · 5. Analyse cycles test · 6. Hypothèses & risques |
| Onglet actif à l'ouverture | Synthèse |

## 3. Onglet « Détail charges » (source de vérité des charges)

**Largeurs de colonnes** : A=9, B=8, C=50, D=15, E=11, F=62, G=12, H=40. **Volets figés** : `C4`.

- Ligne 1 : `A1:H1` fusionnée, texte « DÉTAIL DES CHARGES — COR PHASE 2 (v5) », taille 12, gras, blanc sur `1F3864`, centré.
- Ligne 3 : en-têtes (gras, blanc sur `1F3864`, centrés) : `Lot | ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD)`.
- À partir de la ligne 4, pour **chaque lot** dans l'ordre :
  1. **Ligne de lot** : A = code lot (ex. `LOT 0`), B:D fusionnées = nom du lot ; gras blanc sur `2E75B6` ; E = formule `=E<ligne du sous-total du lot>`.
  2. **Une ligne par tâche** : A vide, B = ID, C = activité, D = profil, E = charge (valeur, police bleue), F = justification, G = dépend de, H = critère de fin. Fond = couleur du profil, sauf tâches dont l'activité contient `[CYCLES TEST]` → fond `FFF9C4` et texte de C en `8B4513`. Colonnes A, B, D, E, G centrées ; C, F, H alignées à gauche avec retour à la ligne.
  3. **Ligne de sous-total** : B:D fusionnées = « Sous-total LOT x », E = `=SUM(E<première tâche>:E<dernière tâche>)`, gras, fond `D9D9D9`.
  4. Une ligne vide.
- **Ligne TOTAL** (après le dernier lot) : A = « ▶ », B:C fusionnées = « TOTAL GÉNÉRAL », D = « DE + MLOps », E = somme des 12 cellules de sous-total (`=E..+E..+…`) ; taille 12, gras, blanc sur `1F3864`. Avec les données ci-dessous, cette ligne est la **ligne 87** (vérification).
- Deux lignes sous le total, en A : légende en italique taille 9 gris `4D4D4D` : « Légende : charges en bleu = valeurs saisies (modifiables) ; sous-totaux et totaux = formules. Lignes jaunes = cycles de test pipeline. »

### 3.1 Données des tâches

#### LOT 0 — Cadrage & essai technique (POC) (sous-total attendu : 4 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T0.1 | Accès COS DCP + lecture d'une photo réelle (7 tables × 7 pays) | Data Engineer | 1 | Vérifier sur données réelles : profondeur 15 mois (prélèvements) / 6 mois (échecs), colonnes vs mapping, nommage fichiers (préfixe + timestamp de dépôt), mode de découpage de la fenêtre par DCP. | — | Rapport de vérification partagé ; écarts vs mapping listés |
| T0.2 | POC PySpark : lecture CSV d'une photo (~25 M lignes) + filtres | Data Engineer | 1 | Mesurer la durée réelle d'un run (base du nombre de cycles de test). Spark sur Kubernetes, comme les recettes PySpark existantes. | T0.1 | Durée de lecture + filtres mesurée et documentée |
| T0.3 | POC PostgreSQL : écriture ~6 mois de DETAILS + publication en transaction | Data Engineer | 1 | Mesurer la vitesse d'écriture et valider le principe 'table de préparation → suppression fenêtre + insertion' en une transaction. | T0.2 | Temps d'écriture mesuré ; publication transactionnelle validée |
| T0.4 | Atelier métier : levée des points ouverts | Data Engineer | 1 | Option A/B (recherche des tentatives précédentes), clé de groupe (règle 4 vs 5), délai max d'échec (docs : ~3 mois / métier : 5 mois), tentatives > 3, définition du mois des KPI, anomalies mapping (règles 6, 9-12, formule taux de succès). | — | Décisions tracées et validées par le métier |

#### LOT 1 — COR_dataset — Lecture des photos DCP (sous-total attendu : 5.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T1.1 | Paramétrage des datasets DCP existants (7 tables) par mois d'arrêté | Data Engineer | 1 | Réutilisation des datasets du data engineer (pointent déjà sur DCP, colonnes définies). Ajout : variable 'mois photo', sélection du fichier par préfixe suivi de chiffres (éviter c_cash_flow_ vs c_cash_flow_ctr_…). | T0.1 | Lecture d'une photo donnée par simple changement de variable |
| T1.2 | Recette de contrôle de complétude de la photo | Data Engineer | 1 | 7 tables × 7 pays présentes et non vides ; lecture de la date de dépôt (timestamp du nom de fichier) pour détecter un redépôt. Arrêt + alerte si incomplet, rien n'est écrit. | T1.1 | Run bloqué si une table/pays manque ; testé sur un cas incomplet |
| T1.3 | Lib filters.py (PySpark) : filtres, sélection de colonnes, typage | Data Engineer | 1.5 | TECH_UPDATE_TYPE_TRUSTED <> 'L', COD_PAYMENT_METHOD = 'DIRECT_DEBIT', COD_CASH_FLOW_DIRECTION = 'CREDIT', ID_LEASING_INVOICE commence par 'FLL'. Lib métier réécrite (schéma différent de la phase 1). | T1.1 | Fonctions de la lib couvertes par tests unitaires |
| T1.4 | Contrats Great Expectations sur les sorties dataset | Data Engineer | 0.5 | Réutilisation de expectation_runner / dataiku_extender de la phase 1 (standard projet). | T1.3 | Contrats générés et passants sur la photo réelle |
| T1.5 | Tests unitaires pytest (lib dataset) | Data Engineer | 0.5 | Même standard que test_prepare_dataset.py de la phase 1. | T1.3 | Tests verts |
| T1.6 | Scénario BUILD_DATASET + cycles de test sur photo réelle | Data Engineer | 1 | Reprise de la structure des scénarios phase 1 (variables, GX_FILES, LOGS). | T1.2, T1.4 | Scénario exécuté de bout en bout sur une photo réelle |

#### LOT 2 — COR_design — Stage 1 (jointures & règles 1-3) (sous-total attendu : 5.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T2.1 | Lib joins.py : jointures des 7 tables | Data Engineer | 1.5 | Clés toujours pays + métier + id. CTR_FIN_CDT_INVOICE ↔ CASH_FLOW (inner) ↔ DIRECT_DEBIT_CASH_FLOW, LEASING_FINANCING_CONDITION, DTM_T_MARCHE_IBL_CTR (left). | T1.6 | Volumétrie après jointure contrôlée (pas de duplication) |
| T2.2 | Règles 1-3 : motif, libellé et date d'échec | Data Engineer | 1 | FAILED_CASH_FLOW + TYP_CASH_FLOW_FAILURE_REASON. Pas de mise à jour ligne à ligne : recalcul de la fenêtre. | T2.1 | Règles 1-3 conformes au mapping sur jeu de test |
| T2.3 | Périodicité / marché / IBL : dernière valeur connue | Data Engineer | 0.5 | Décision validée (option A) : dernière valeur pendant la vie de la ligne, figée ensuite. | T2.1 | Valeurs présentes sur toutes les lignes de la fenêtre |
| T2.4 | Recette PySpark Stage 1 (flux unique 7 pays) | Data Engineer | 0.5 | Un seul flux partitionné par pays au lieu de 7 recettes (×7) comme en phase 1. | T2.2, T2.3 | Recette exécutée sur la photo réelle |
| T2.5 | Tests unitaires + contrats GX Stage 1 | Data Engineer | 1 | Standard phase 1. | T2.4 | Tests verts ; contrats passants |
| T2.6 | [CYCLES TEST] Stage 1 | Data Engineer | 1 | ~4 runs (voir onglet Analyse cycles test). Durée par run à confirmer au POC (T0.2). | T2.4 | Sortie Stage 1 stable |

#### LOT 3 — COR_design — Stage 2 (groupes, ordre, flags, fenêtre) (sous-total attendu : 9 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T3.1 | Lib business_rules.py — règles 4-6 (groupe, ordre, date du DD initial) | Data Engineer | 3 | Option B : tentatives précédentes cherchées dans les 15 mois de la photo ET dans les mois figés de DETAILS (conforme aux règles 4-6 du mapping). Calcul en une passe (tri par facture + date) au lieu du multi-pass ligne à ligne. | T2.6 | Groupes/ordres conformes aux exemples des slides 15-17 (session 1) |
| T3.2 | Règles 7-12 : les 6 flags | Data Engineer | 1 | Ordre 1 / 2 / 3 × émis / en échec. Ordre > 3 non flagué (validé métier). | T3.1 | Flags conformes sur jeu de test |
| T3.3 | Fenêtre de recalcul M-5 → M + colonnes de traçabilité | Data Engineer | 0.5 | Ne garder que les lignes émises entre M-5 et M ; colonnes mois de la photo + date du run. | T3.2 | Seuls les 6 mois de la fenêtre sont produits |
| T3.4 | Tests unitaires — jeux séquentiels | Data Engineer | 2 | Cas : groupe sur plusieurs mois, frontière de fenêtre, échec tardif (5 mois), suppression logique ('L'), redépôt, facture déjà connue dans les mois figés. | T3.1 | Tous les cas listés testés et verts |
| T3.5 | [CYCLES TEST] Stage 2 | Data Engineer | 2 | ~5 runs : règles 4-6 = bugs subtils visibles uniquement en run complet. | T3.3 | Sortie Stage 2 stable |
| T3.6 | Scénario BUILD_DESIGN + test bout en bout design | Data Engineer | 0.5 | Enchaînement Stage 1 → Stage 2. | T3.5 | Scénario exécuté sans erreur |

#### LOT 4 — COR_product — DETAILS (sous-total attendu : 4 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T4.1 | Tables PostgreSQL DETAILS + DETAILS_TMP + index | Data Engineer | 0.5 | Index pays + mois d'émission. | T0.3 | Tables créées ; index en place |
| T4.2 | Recette d'écriture DETAILS_TMP (fenêtre de 6 mois) | Data Engineer | 0.5 | Table de préparation non visible par Power BI. | T3.6, T4.1 | DETAILS_TMP alimentée |
| T4.3 | Contrôles qualité avant publication | Data Engineer | 1 | Doublons sur la clé, colonnes obligatoires, volumes par pays/mois vs run précédent (seuil). Échec = arrêt, rien publié. | T4.2 | Contrôles bloquants testés (cas OK et KO) |
| T4.4 | Publication en transaction (Execute SQL) | Data Engineer | 1 | Suppression des mois M-5 → M de DETAILS + insertion depuis DETAILS_TMP, tout ou rien. | T4.3 | Relance = même résultat (idempotence vérifiée) |
| T4.5 | Purge > 4 ans | Data Engineer | 0.5 | Conservation 4 ans glissants (note d'historisation). | T4.4 | Purge testée |
| T4.6 | Tests + [CYCLES TEST] DETAILS | Data Engineer | 0.5 |  | T4.4 | DETAILS validée sur photo réelle |

#### LOT 5 — COR_product — KPI & reprise phase 1 (sous-total attendu : 6 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T5.1 | KPI en SQL : 7 axes, compteurs, montants, taux — fenêtre 6 mois | Data Engineer | 2 | Annule & Remplace des 6 derniers mois (conforme note d'historisation), plus de recalcul complet. | T4.4 | KPI recoupés avec DETAILS |
| T5.2 | Reprise unique des KPI phase 1 (< février 2026) | Data Engineer | 2 | Union des 7 tables xx_var_stats (PostgreSQL phase 1) → schéma cible, ajustement de la colonne qui diffère, colonne SOURCE. Pas de backfill 48 mois depuis les sources. | T0.4 | Historique ≥ 4 ans disponible dans KPI |
| T5.3 | Publication KPI (KPI_TMP + remplacement atomique) | Data Engineer | 0.5 | Power BI ne voit jamais un état intermédiaire. | T5.1 | Publication testée |
| T5.4 | Tests + [CYCLES TEST] KPI | Data Engineer | 1.5 | Recoupement KPI ↔ DETAILS, continuité phase 1 / phase 2 à février 2026. | T5.3 | KPI validés sur photo réelle |

#### LOT 6 — Orchestration & exploitation (sous-total attendu : 5.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T6.1 | Scénario mensuel chaîné (DATASET → DESIGN → PRODUCT) | MLOps | 1.5 | Déclencheur temporel à jour fixe après le 7 du mois, variable mois photo (comme DAILY_CHECK → BUILD_* en phase 1). | T3.6 | Run mensuel complet déclenché automatiquement |
| T6.2 | Journal des runs + détection de redépôt | MLOps | 1 | Mois photo, date de dépôt de chaque fichier, volumes, statut. | T6.1 | Journal alimenté à chaque run |
| T6.3 | Alertes (succès / échec / photo incomplète / contrôle KO) | MLOps | 0.5 | Étape Send message des scénarios. | T6.1 | Alertes reçues dans chaque cas |
| T6.4 | Mode rejeu / reconstruction | MLOps | 1 | Rejeu d'un mois donné ; rejeu chronologique d'une plage de photos (reconstruction). | T6.1 | Reconstruction d'une plage testée |
| T6.5 | Tests bout en bout + performance sur volumétrie réelle | MLOps | 1.5 |  | T5.4, T6.4 | Durée du run mensuel mesurée et acceptée |

#### LOT 7 — Démarrage (initialisation) (sous-total attendu : 1.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T7.1 | Rejeu des photos juillet → septembre 2026 (et suivantes disponibles) | Data Engineer | 0.5 | Première photo : juillet 2026 → février à juillet 2026 créés, puis rejeu chronologique. | T6.4 | DETAILS et KPI remplis depuis février 2026 |
| T7.2 | Vérifications de cohérence février → septembre 2026 | Data Engineer | 1 |  | T7.1 | Volumes et continuité validés |

#### LOT 8 — Recette fonctionnelle (UAT) (sous-total attendu : 5.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T8.1 | Comparaison phase 1 / phase 2 sur les mois communs + analyse des écarts | Data Engineer | 2 | Phase 1 toujours en production : comparaison à partir de février 2026. Écarts attendus (nouvelle logique de comptage) à expliquer. | T7.2 | Écarts expliqués et validés par le métier |
| T8.2 | Support métier pendant la recette | Data Engineer | 1.5 |  | T7.2 | PV de recette |
| T8.3 | Corrections post-recette | Data Engineer | 2 | Chaque correction = nouveau cycle de test. | T8.1 | Anomalies bloquantes corrigées |

#### LOT 9 — Documentation technique (sous-total attendu : 1.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T9.1 | Architecture & mécanisme (fenêtre 6 mois, rejeu, reprise phase 1) | Data Engineer | 0.75 |  | T8.3 | Document publié |
| T9.2 | Guide d'exploitation (redépôt, photo incomplète, reconstruction) | Data Engineer | 0.75 |  | T8.3 | Guide publié |

#### LOT 10 — Gestion de projet & coordination (sous-total attendu : 1.5 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T10.1 | Points d'avancement & coordination | Data Engineer | 1.5 | Réparti sur toute la durée. | — | — |

#### LOT 11 — Évolution specs & marge technique (sous-total attendu : 3 j)

| ID | Activité | Profil | Charge (j) | Commentaire / Justification | Dépend de | Critère de fin (DoD) |
|---|---|---|---|---|---|---|
| T11.1 | Évolution des specs suite aux points ouverts | Data Engineer | 1.5 | Marge volontairement réduite : voir onglet Hypothèses & risques. | — | — |
| T11.2 | Edge cases données (CSV, encodage, valeurs inattendues) | Data Engineer | 1.5 |  | — | — |

**Contrôles** : total = **52.5 j** ; Data Engineer = **47 j** ; MLOps = **5.5 j**.

## 4. Onglet « Synthèse »

**Largeurs** : A=9, B=52, C=18, D=14, E=14.

- `A1:E1` fusionnée : « CHIFFRAGE COR PHASE 2 — Data Products Direct Debits Cash Flow » — taille 13, gras, blanc sur `1F3864`, centré.
- `A2:E2` fusionnée : « v5 — Recalcul « Annule & Remplace » sur 6 mois depuis la photo DCP mensuelle | 7 pays × 2 data products | flux unique | sans backfill 48 mois » — taille 9, texte `1F3864` sur `D9E1F2`, centré, retour à la ligne, hauteur de ligne 26.
- Ligne 4 : en-têtes `Lot | Description | Profil | Charge (j) | % Total` (gras blanc sur `1F3864`, centrés).
- Lignes 5 à 16 : une ligne par lot (LOT 0 à LOT 11). A = code lot (centré), B = nom du lot, C = profil du lot (profil de ses tâches), D = `='Détail charges'!E<ligne sous-total du lot>` (centré), E = `=IF($D$<ligne total>=0,0,D<ligne>/$D$<ligne total>)` format `0.0%`. Fond = `BDD7EE` (Data Engineer) ou `E2EFDA` (MLOps) ; LOT 9, 10, 11 en `F2F2F2`.
- Ligne 18 : « Sous-total Data Engineer » ; ligne 19 : « Sous-total MLOps ». B = libellé, C = profil, D = `=SUMIF($C$5:$C$16,C<ligne>,$D$5:$D$16)`, E = % du total (format `0.0%`), gras, fond `D9D9D9`.
- Ligne 20 : TOTAL. A = « ▶ », B = « TOTAL GÉNÉRAL », C = « DE + MLOps », D = `=SUM(D5:D16)`, E = `=IF(D20=0,0,D20/D20)` format `0%` ; taille 12, gras, blanc sur `1F3864`.
- Bloc de contrôle (lignes 22 à 27, libellé en B, valeur en D) :

| Ligne | B (libellé) | D (valeur / formule) | Mise en forme |
|---|---|---|---|
| 22 | Jours ouvrés par mois (hypothèse) | `21` | fond `FFFF00`, valeur bleue, commentaire « Hypothèse : 21 jours ouvrés par mois en moyenne. Modifiable. » |
| 23 | Plafond demandé (mois) | `2.5` | fond `FFFF00`, valeur bleue, commentaire « Plafond fixé par le demandeur : 2,5 mois. » |
| 24 | Charge totale en mois | `=IF(D22=0,0,D20/D22)` | gras, format `0.00` → attendu 2,50 |
| 25 | Charge Data Engineer en mois (chemin critique) | `=IF(D22=0,0,D18/D22)` | gras, format `0.00` → attendu 2,24 |
| 26 | Durée calendaire planifiée (semaines) | `=MAX(Planning!F:F)` | gras → attendu 11 |
| 27 | Respect du plafond (charge totale ≤ plafond) | `=IF(D24<=D23,"OK","DÉPASSEMENT")` | gras → attendu OK |

- À partir de la ligne 29 : hypothèses, une par ligne, chaque ligne fusionnée A:E, taille 9, gris `4D4D4D`, retour à la ligne, hauteur 30 (15 pour le titre en gras) :

  - Hypothèses principales :
  - • Mécanisme : chaque mois, la photo DCP M recalcule et remplace les mois d'émission M-5 → M (note d'historisation : « Annule & Remplace » 5 mois + insert du nouveau mois). Mois plus anciens figés.
  - • Pas de backfill 48 mois : la plus ancienne photo DCP est juillet 2026 (→ février 2026). L'historique antérieur vient d'une reprise unique des KPI de la phase 1 (PostgreSQL, ≥ 4 ans).
  - • Flux unique pour les 7 pays (tables DCP contiennent le pays) au lieu de 7 recettes par étape comme en phase 1 — à valider (impact si ×7 : voir onglet Hypothèses & risques).
  - • Règles 4-6 en option B (photo 15 mois + mois figés de DETAILS) ; option A (photo seule) = environ -1 j.
  - • Standards phase 1 réutilisés : 3 projets DATASET / DESIGN / PRODUCT, lib + recettes courtes, Great Expectations, pytest, scénarios chaînés.
  - • Hors périmètre : déploiement et environnements (dev → test → prod).
  - • Profil : développeur senior Dataiku / PySpark confirmé + MLOps à temps partiel.

## 5. Onglet « Planning » (Gantt piloté par formules)

**Largeurs** : A=8, B=58, C=15, D=10, E=10, F=10, G à Q (11 semaines) = 6,5. **Volets figés** : `G6`.

- `A1:Q1` fusionnée : « PLANNING — COR PHASE 2 (v5) — semaines S1 à S11 (≈ 2,5 mois) », taille 12, gras, blanc sur `1F3864`.
- `B2` = « Date de démarrage (lundi) : » (gras) ; `C2` = date **12/10/2026** (format `dd/mm/yyyy`, gras bleu, fond `FFFF00`, commentaire « Hypothèse : démarrage le lundi 12/10/2026. À remplacer par la date réelle ; les dates des semaines se recalculent. »).
- Ligne 3, colonnes G à Q : numéros de semaine 1 à 11 (valeurs techniques, police taille 1 blanche = invisibles) — servent à la mise en forme conditionnelle.
- Ligne 4 : en-têtes `ID | Lot / Tâche | Profil | Charge (j) | Sem. début | Sem. fin | S1 … S11` (gras blanc sur `1F3864`, centrés).
- Ligne 5 : B = « Début de semaine → » ; G5 à Q5 = `=$C$2+7*k` avec k = 0…10 (format `dd/mm`, taille 8, blanc sur `154360`).
- À partir de la ligne 6, pour chaque lot :
  - **Ligne de lot** (gras blanc sur `2E75B6`) : A = code lot, B = nom, C vide, D = `='Détail charges'!E<sous-total du lot>`, E = `=MIN(E<1re tâche>:E<dernière tâche>)`, F = `=MAX(F<1re tâche>:F<dernière tâche>)` ; cellules G:Q fond `DDEBF7`.
  - **Lignes de tâche** (taille 9) : A = ID, B = activité, C = profil, D = `='Détail charges'!E<ligne de la tâche>`, E = semaine début, F = semaine fin (valeurs en bleu, modifiables).
- **Mise en forme conditionnelle** sur `G6:Q<dernière ligne>` (3 règles, formules relatives à G6) :
  - `=AND(G$3>=$E6,G$3<=$F6,$C6="Data Engineer")` → fond `2E75B6`
  - `=AND(G$3>=$E6,G$3<=$F6,$C6="MLOps")` → fond `70AD47`
  - `=AND(G$3>=$E6,G$3<=$F6,$C6="")` → fond `9DC3E6` (étendue des lots)
- Notes sous le tableau (une ligne vide puis 3 lignes fusionnées A:Q, italique taille 9 gris) :
  - « Légende : bleu foncé = Data Engineer ; vert = MLOps ; bleu clair = étendue du lot. Semaines début / fin en bleu = modifiables (le diagramme se met à jour). »
  - « Chemin critique : POC → DATASET → DESIGN Stage 1 → Stage 2 → DETAILS → KPI → Démarrage → Recette. Le MLOps travaille en parallèle à partir de S6 (scénario design disponible). Charge Data Engineer ≈ 4 à 5 j par semaine. »
  - « S11 = semaine tampon (marge LOT 11). La gestion de projet (LOT 10) est répartie sur toute la durée. »

### 5.1 Semaines par tâche

| ID | Sem. début | Sem. fin |
|---|---|---|
| T0.1 | 1 | 1 |
| T0.2 | 1 | 1 |
| T0.3 | 1 | 1 |
| T0.4 | 1 | 1 |
| T1.1 | 2 | 2 |
| T1.2 | 2 | 2 |
| T1.3 | 2 | 2 |
| T1.4 | 2 | 3 |
| T1.5 | 3 | 3 |
| T1.6 | 3 | 3 |
| T2.1 | 3 | 3 |
| T2.2 | 3 | 4 |
| T2.3 | 4 | 4 |
| T2.4 | 4 | 4 |
| T2.5 | 4 | 4 |
| T2.6 | 4 | 4 |
| T3.1 | 4 | 5 |
| T3.2 | 5 | 5 |
| T3.3 | 5 | 5 |
| T3.4 | 5 | 6 |
| T3.5 | 6 | 6 |
| T3.6 | 6 | 6 |
| T4.1 | 6 | 6 |
| T4.2 | 6 | 6 |
| T4.3 | 7 | 7 |
| T4.4 | 7 | 7 |
| T4.5 | 7 | 7 |
| T4.6 | 7 | 7 |
| T5.1 | 7 | 7 |
| T5.2 | 8 | 8 |
| T5.3 | 8 | 8 |
| T5.4 | 8 | 8 |
| T6.1 | 6 | 6 |
| T6.2 | 6 | 7 |
| T6.3 | 7 | 7 |
| T6.4 | 7 | 7 |
| T6.5 | 8 | 9 |
| T7.1 | 9 | 9 |
| T7.2 | 9 | 9 |
| T8.1 | 9 | 9 |
| T8.2 | 9 | 10 |
| T8.3 | 10 | 10 |
| T9.1 | 10 | 10 |
| T9.2 | 10 | 10 |
| T10.1 | 1 | 11 |
| T11.1 | 11 | 11 |
| T11.2 | 11 | 11 |

## 6. Onglet « Écarts vs v4 »

**Largeurs** : A=44, B=12, C=12, D=12, E=80. `A1:E1` fusionnée : « ÉCARTS ENTRE LE CHIFFRAGE v4 (Option C) ET LE CHIFFRAGE v5 » (gras blanc sur `1F3864`).

Ligne 3 : en-têtes `Thème | v4 (j) | v5 (j) | Écart (j) | Raison du changement`. Une ligne par thème (hauteur 42, retour à la ligne) : B = valeur v4 (bleue), C = formule vers le(s) sous-total(aux) de « Détail charges », D = `=C-B`. Ligne TOTAL (gras blanc sur `1F3864`) : B, C, D = `SUM` de la colonne ; E = « Source v4 : Chiffrage_COR_Phase2_OptionC_v4.xlsx (onglet Synthèse). »

| Thème | v4 (j) | v5 = sous-total de | Raison du changement |
|---|---|---|---|
| Cadrage & essai technique (POC) | 0 | LOT 0 | Nouveau lot : vérifier une vraie photo DCP et mesurer Spark / PostgreSQL avant de développer (en v4, l'analyse specs était répartie dans les lots 1, 2 et 10). |
| COR_dataset | 9 | LOT 1 | Datasets du data engineer réutilisés (pointent déjà sur DCP, colonnes définies). Un seul flux pour 7 pays au lieu de 7 recettes. |
| COR_design — jointures & règles 1-3 (v4 : lots 2 + 3) | 14 | LOT 2 | Flux unique au lieu de ×7 ; moins de cycles de test (1 photo par run). |
| COR_design — règles 4-12 (v4 : lot 4) | 13 | LOT 3 | Calcul en une passe (tri par facture) au lieu du multi-pass ligne à ligne ; fenêtre de 6 mois ajoutée ; flux unique. |
| COR_product — DETAILS (v4 : lot 5) | 4.5 | LOT 4 | Ajout des contrôles avant publication et de la publication en transaction ; flux unique. |
| COR_product — KPI & historisation (v4 : lot 6) | 14 | LOT 5 | Suppression du backfill 48 mois × 7 pays (~1,85 Md lignes) : photos DCP disponibles seulement depuis juillet 2026 → reprise unique des KPI phase 1. Annule & Remplace 6 mois au lieu d'un mécanisme par mois avec checkpoints. |
| MLOps & orchestration (v4 : lot 7) | 9 | LOT 6 | Déploiement multi-environnements hors périmètre. Ajout du journal des runs et du mode rejeu / reconstruction. |
| Démarrage (initialisation) | 0 | LOT 7 | Nouveau : rejeu des photos juillet → septembre 2026 (remplace le backfill). |
| Recette fonctionnelle (v4 : lot 8) | 7 | LOT 8 | Recette centrée sur la comparaison phase 1 / phase 2 sur les mois communs. |
| Documentation (v4 : lot 9) | 3 | LOT 9 | Un seul flux à documenter au lieu de 7. |
| Gestion de projet (v4 : lot 10) | 4 | LOT 10 | Analyse des specs et cadrage déjà réalisés (conception validée) ; reste le suivi. |
| Évolution specs & marge (v4 : lot 11) | 8 | LOT 11 | Marge réduite pour tenir 2,5 mois : risque assumé, voir onglet Hypothèses & risques. |

Contrôle : TOTAL v4 = 85,5 ; v5 = 52,5 ; écart = −33.

## 7. Onglet « Analyse cycles test »

**Largeurs** : A=36, B=16, C=22, D=14, E=62. `A1:E1` fusionnée : « ANALYSE — Cycles de test pipeline (v5) » (gras blanc sur `C55A11`). Ligne 3 : en-têtes `Lot / Stage | Nb runs estimés | Durée moy/run | Charge (j) | Justification`. Lignes alternées `FCE4D6` / `FFFFFF`, taille 9. Colonne C = « à mesurer (T0.2) » partout. Colonne D = formule vers la ligne de la tâche indiquée dans « Détail charges ».

| Lot / Stage | Nb runs estimés | Charge = tâche | Justification |
|---|---|---|---|
| LOT 1 — DATASET (1 flux) | ~3 runs | T1.6 | Lecture + contrôle de complétude + filtres sur une photo réelle. |
| LOT 2 — Stage 1 (1 flux) | ~4 runs | T2.6 | Jointures : erreurs de clés, nulls, types. |
| LOT 3 — Stage 2 (1 flux) | ~5 runs | T3.5 | Règles 4-6 : bugs subtils visibles uniquement en run complet. |
| LOT 4 — DETAILS | ~2 runs | T4.6 | Écriture + publication + contrôles. |
| LOT 5 — KPI | ~3 runs | T5.4 | Validation des agrégations et de la continuité avec la phase 1. |
| LOT 6 — Bout en bout | ~2 runs | T6.5 | Scénario mensuel complet + mesure de performance. |

- Une ligne vide, puis « TOTAL cycles de test » (gras) : D = `SUM` des 6 lignes (attendu 7,5) ; E = `=D<ligne>/'Détail charges'!E87` au format `0.0%" du total"` (attendu 14,3 %).
- Deux lignes plus bas, `A:E` fusionnées sur 2 lignes, italique taille 9 gris : « Note : en v4 un run durait 2 à 5 h (pipeline phase 1, ×7 pays). En v5 un run traite une seule photo (~25 M lignes, 7 pays) en PySpark : la durée réelle sera mesurée au POC (T0.2). Pendant le développement, travailler sur un pays ou un échantillon réduit pour raccourcir les cycles. »

## 8. Onglet « Hypothèses & risques »

**Largeurs** : A=7, B=60, C=14, D=46, E=40. `A1:E1` fusionnée : « HYPOTHÈSES, POINTS À CONFIRMER ET RISQUES » (gras blanc sur `1F3864`). Ligne 3 : en-têtes `ID | Hypothèse / risque | Impact (j) | Si l'hypothèse tombe | Levée / mitigation`. Taille 9, retour à la ligne, hauteur 32. Fond : lignes H alternées `FFFFFF` / `F2F2F2` ; lignes R en `FFF2CC`. Colonnes A et C centrées.

| ID | Hypothèse / risque | Impact (j) | Si l'hypothèse tombe | Levée / mitigation |
|---|---|---|---|---|
| H1 | Un seul flux Dataiku pour les 7 pays (écart au standard phase 1 : 7 recettes par étape). | +6 à +8 | Retour à 7 recettes par étape : recettes, tests et cycles multipliés. | Validation du chef de projet avant démarrage. |
| H2 | Règles 4-6 en option B (photo 15 mois + mois figés de DETAILS). | -1 | Option A (photo seule) si le métier garantit qu'aucun prélèvement n'arrive > 15 mois après le premier. | Atelier métier T0.4. |
| H3 | Photos DCP conservées sans limite et jamais modifiées (hors redépôt). | +5 à +8 | Il faudrait une copie de l'historique dans DLP (couche intermédiaire). | Engagement écrit de DCP. |
| H4 | La photo contient 15 mois de prélèvements et 6 mois d'échecs (slides 8-10, session 1). | +2 à +4 | Si moins de 11 mois de prélèvements : lecture obligatoire des mois figés de DETAILS pour toutes les tentatives. | Vérification T0.1. |
| H5 | KPI phase 1 disponibles ≥ 4 ans en PostgreSQL ; une seule colonne diffère. | +1 à +3 | Mapping de reprise plus lourd. | Analyse des 7 tables xx_var_stats en T5.2. |
| H6 | Déploiement et environnements hors périmètre. | +2 à +3 | Chiffrage v4 : 1 j de configuration multi-env + tests. | Confirmé par le demandeur. |
| H7 | Durée d'un run compatible avec ~19 cycles de test (voir Analyse cycles test). | +2 à +5 | Run trop long → moins d'itérations par jour. | Mesure au POC (T0.2) ; dev sur échantillon. |
| H8 | 21 jours ouvrés par mois ; 1 Data Engineer senior à temps plein + 1 MLOps à temps partiel. | — | Profil junior ou temps partiel → durée calendaire allongée. | Affectation confirmée avant démarrage. |
| R1 | Marge réduite à 3 j (v4 : 8 j) pour tenir 2,5 mois. | — | Tout imprévu > 3 j dépasse le plafond. | Leviers : documentation réduite, recette en parallèle des corrections, MLOps en avance. |
| R2 | Anomalies du mapping (règle 6 sur le mauvais champ, renvois des règles 9-12, formule du taux de succès, versionnement). | +1 à +2 | Reprises de développement. | Atelier métier T0.4. |
| R3 | Écarts phase 1 / phase 2 (nouvelle logique de comptage) difficiles à expliquer. | +1 à +3 | Recette prolongée. | Préparer l'analyse des écarts dès T7.2. |
| R4 | Disponibilité du métier pendant la recette. | — | Glissement calendaire. | Réserver les créneaux de recette dès le démarrage. |

## 9. Vérifications à faire après construction

1. Recalculer le classeur (Excel ou LibreOffice) : **0 erreur de formule**.
2. Synthèse : total = 52,5 ; Data Engineer = 47 ; MLOps = 5,5 ; charge totale = 2,50 mois ; durée = 11 semaines ; contrôle = « OK ».
3. Les sous-totaux de « Détail charges » correspondent aux sous-totaux attendus de la section 3.1.
4. Écarts vs v4 : 85,5 / 52,5 / −33.
5. Planning : dates S1 = 12/10, S11 = 21/12 ; les barres colorées apparaissent entre semaine début et fin ; changer `C2` décale toutes les dates.
6. Modifier une charge dans « Détail charges » met à jour Synthèse, Planning, Écarts et Analyse cycles test.
