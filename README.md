# Hoe Aona

Application web responsive d'analyse de la désinformation. Elle reçoit un texte, une image, un document, un audio ou des liens. Elle repère les affirmations vérifiables et cherche des preuves auprès de sources fiables via un serveur MCP. Elle écarte les sources générées par IA, puis donne trois scores sur 10 (source, véracité des données, part d'IA) et un score global. Chaque argument renvoie à une preuve (lien, extrait, image, statistique datée), et un article prêt à publier est proposé.

Les rédactions disposent aussi d'un **mini réseau social** pour publier leurs contenus et analyses, d'un **espace personnel** (back office) où chaque compte gère sa propre base d'informations traitées, et d'une **administration** pour les comptes et la modération.

L'analyse du besoin, la méthode de calcul et les limites sont décrites dans [docs/ANALYSE.md](docs/ANALYSE.md).

## Architecture

```
frontend/   Angular 20 (composants autonomes, signals) : Connexion, Fil, Analyser, Résultat, Mon espace,
            Historique, Profil, Paramètres, Administration
backend/    FastAPI
  app/auth.py           comptes (PBKDF2) et sessions (cookie HttpOnly)
  app/routers/          analyses, réseau social, administration, comptes, paramètres
  app/mcp/server.py     serveur MCP « hoe-aona-tools » (FastMCP, stdio)
  app/mcp/gateway.py    client MCP utilisé par le pipeline
  app/tools/            Wikipedia, GDELT, Tavily, Banque mondiale, lecture de page, Sightengine
  app/services/         extraction, détection IA, affirmations, preuves, évaluation, scores, article
docs/ANALYSE.md         analyse du projet
```

## Installation locale

Prérequis : Python 3.11 ou plus, Node.js 20.19+ ou 22.12+.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # puis renseignez les clés gratuites (voir plus bas)
uvicorn app.main:app --reload
```

L'API répond sur http://localhost:8000 et sa documentation interactive sur http://localhost:8000/docs.

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Ouvrez http://localhost:4200. Les appels `/api` sont relayés vers le backend par `proxy.conf.json`.

### Avec Docker

```bash
cp backend/.env.example backend/.env   # renseignez les clés
docker compose up --build
```

L'application complète est servie sur http://localhost:8000.

## Sources des preuves (public cible : Madagascar)

Pour chaque affirmation, le back office interroge en parallèle :

| Source | Ce qu'elle apporte | Clé |
| --- | --- | --- |
| Tavily limité aux **sites officiels et à la presse malgaches** | INSTAT, BFM, MEF, BNGRC, CENI, HCC… et L'Express, Midi Madagasikara, Newsmada… | `TAVILY_API_KEY` |
| NewsData.io (`country=mg`) | Presse malgache des dernières 48 h | `NEWSDATA_API_KEY` |
| GDELT DOC 2.0 | Presse mondiale des 3 derniers mois (requêtes mises en file : 1 toutes les 5 s) | non |
| Tavily (web général), Wikipedia | Contexte | `TAVILY_API_KEY` |
| **FMI** (World Economic Outlook) et Banque mondiale | Statistiques officielles : estimation de l'année en cours (FMI) et dernière valeur publiée (Banque mondiale), avec série, date de mise à jour et lien vers la page Madagascar | non |
| **Fil média de la plateforme** | Publications des rédactions membres proches de l'affirmation (fiabilité 55 %, 65 % avec une analyse jointe) ; elles ne suffisent jamais seules | non |

Chaque preuve indique son lien, son extrait, sa date de publication, sa fiabilité, l'outil qui l'a trouvée et un badge **Source officielle** le cas échéant. Une statistique de plus de deux ans est signalée.

Sous chaque affirmation, le bloc **Qui contacter pour confirmer** propose les institutions compétentes (site, téléphone, e-mail) tirées de l'**annuaire des sources officielles** (`/sources`). L'annuaire est prérempli avec 21 institutions dont les coordonnées ont été relevées le 2 novembre 2026 sur leurs propres sites ; les administrateurs l'enrichissent (ministères de la Santé, du Commerce, de l'Agriculture… dont le site n'a pas pu être vérifié) et tiennent les mots-clés à jour.

## Langues : malagasy, français, anglais

L'interface est disponible en **malagasy**, **français** et **anglais**. Le sélecteur MG / FR / EN se trouve sur l'écran de connexion, dans la barre latérale (menu « Plus » sur téléphone) et dans les Paramètres. Le choix est mémorisé dans le navigateur ; à défaut, la langue du navigateur est utilisée.

- Pour un compte connecté, changer de langue règle aussi la **langue des contenus rédigés par l'IA** : résumé, conclusions, tests de raisonnement et article.
- Dates et nombres suivent la langue choisie.
- Dans le code, chaque texte est écrit en français et passe par le traducteur : `{{ 'Fil média' | t }}`, `t('Analyse supprimée')`, `{{ n | plural: '{n} analyse' : '{n} analyses' }}`. Les traductions sont dans `frontend/src/app/i18n/en.ts` et `mg.ts` ; un texte absent s'affiche en français.
- `python scripts/check_i18n.py` signale toute clé sans traduction.
- Les traductions malgaches sont à faire relire par un locuteur natif de la rédaction avant une mise en service.

## Application mobile et vérification physique

`FrontendMobile/` est l'application Android (Java, Material 3). Elle reprend les fonctions du web : fil média (publications avec image et analyse jointe, J'apprécie, commentaires, modération), analyse de texte, de liens et de fichiers avec suivi en direct, page Résultat complète, Mon espace (suivi éditorial, étiquettes, notes, export CSV), annuaire des sources officielles, statistiques, profil, paramètres, administration, interface en malagasy, français et anglais.

Elle ajoute une fonction **réservée au mobile** : la **vérification physique**. Certaines informations récentes ne se vérifient que sur place.

1. Un membre décrit l'information et désigne le lieu précis sur une carte OpenStreetMap. Il peut aussi partir d'une affirmation de la page Résultat.
2. PostGIS sélectionne les comptes dont la dernière position (moins de 2 heures) se trouve à moins de **2 km** du lieu (`ST_DWithin` sur des `geography`). Ces comptes reçoivent une notification.
3. Le premier qui accepte devient vérificateur. L'attribution est atomique : le demandeur est notifié, et l'annonce disparaît chez les autres (liste et volet de notifications).
4. Le vérificateur se rend sur place et indique si l'information est **correcte**, **incorrecte** ou **impossible à établir**, avec un commentaire et une photo. Le demandeur est notifié.

Le vérificateur peut renoncer : la demande est alors proposée de nouveau. Le demandeur peut annuler. Une demande sans preneur expire au bout de 24 heures.

**Confidentialité des positions**

- Le partage est désactivé par défaut. Il demande un consentement explicite.
- Aucune route ne renvoie de coordonnées d'un compte, de distance ni de nombre de destinataires, pas même aux administrateurs. Seule la base calcule qui est dans le rayon.
- La position est effacée quand l'option est désactivée, à la déconnexion et à la désactivation du compte. Une position de plus de 2 heures n'est plus prise en compte et est purgée au démarrage.
- Le nom du vérificateur n'est montré au demandeur qu'après acceptation. L'application le signale avant d'accepter.
- Les routes `/api/verifications/*` exigent l'en-tête `X-Hoe-Client: android`, envoyé par l'application. C'est une restriction d'usage, pas une mesure de sécurité.

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `POSTGIS_URL` | vide | `postgresql://…` avec l'extension PostGIS ; vide = fonction désactivée |
| `VERIFICATION_RADIUS_M` | `2000` | Rayon de notification |
| `VERIFICATION_HOURS` | `24` | Durée de vie d'une demande sans preneur |
| `LOCATION_MAX_AGE_MINUTES` | `120` | Âge maximal d'une position prise en compte |

`docker compose up` démarre aussi un conteneur `postgis/postgis`. Les notifications arrivent par interrogation : toutes les 30 s quand l'application est ouverte, toutes les 15 min sinon (WorkManager). Application fermée, la position n'est mise à jour que si l'utilisateur accorde la localisation en arrière-plan.

**Constat certifié**

Le constat est conçu pour résister à un vérificateur qui tricherait.

- **Capture verrouillée** : la photo se prend avec l'appareil photo, depuis l'application ; la galerie n'est pas proposée. Avant la prise de vue, l'application demande au serveur un jeton à usage unique (`POST /api/verifications/{id}/capture`). La photo doit arriver dans les `CAPTURE_TOKEN_MINUTES`, avec des données EXIF d'appareil photo et une heure de prise de vue postérieure au jeton.
- **Présence sur place** : la position au moment du constat sert à calculer la distance au lieu avec PostGIS. Seule une tranche est conservée (« moins de 150 m »), jamais les coordonnées. Il faut être à moins de `VERIFICATION_ON_SITE_M`, avec une précision GPS suffisante et une position non simulée.
- **Certificat signé** : l'empreinte SHA-256 de la photo, les contrôles et le verdict sont signés en Ed25519 par le serveur. La clé est créée dans `data/attestation_ed25519.pem`, et la clé publique est servie par `GET /api/attestations/public-key`. `POST /api/attestations/verify` retrouve le certificat d'une photo. Une photo retouchée ou recadrée n'a plus la même empreinte et n'est donc pas reconnue.
- **Second avis indépendant** : si un contrôle échoue, ou si le demandeur conteste (`POST /api/verifications/{id}/dispute`), la demande repart vers un autre membre proche. Il ne voit pas le premier constat avant de rendre le sien. Le résultat final est « confirmé par deux vérificateurs » ou « constats divergents ».

Il s'agit d'un certificat inspiré de C2PA, pas d'une implémentation C2PA. L'EXIF peut être falsifié par un utilisateur averti : la défense repose sur la combinaison des contrôles et sur le second avis.

**Activité par région et deepfakes (données fictives)** : `GET /api/stats/activity` alimente, dans la page Statistiques (web et mobile), le taux d'activité des 23 régions (analyses pour 100 000 habitants, volume, tendance sur un mois) et le taux de contenus truqués repérés (par type et par mois). **Ces chiffres sont générés** par `app/services/demo_activity.py`, de façon déterministe. L'API les marque `demo: true` et l'interface affiche « Données fictives de démonstration ». Il faudra les remplacer par un calcul sur les vraies analyses avant toute mise en service.

**Construire l'application** : ouvrez `FrontendMobile/` dans Android Studio. Par défaut, l'application vise `http://10.0.2.2:8000/` (la machine hôte vue depuis l'émulateur). Pour un téléphone, changez l'adresse dans « Serveur » sur l'écran de connexion, ou construisez avec `-PhoeApiUrl=http://IP:8000/`. Le HTTP en clair n'est autorisé qu'en debug.

## Données de démonstration

```bash
cd backend
python -m app.demo_feed            # fil média : 6 rédactions fictives, 6 analyses, 10 publications
python -m app.demo_feed --reset    # recrée
python -m app.demo_feed --remove   # supprime tout ce qui a été créé
```

Les comptes (`rindra`, `hery`, `fara`, `tojo`, `mialy`, `lova` `@demo.hoe-aona.mg`, mot de passe `demo-hoe-aona`) portent la mention « Compte fictif de démonstration ». Les médias, les personnes et les sources sont inventés, et les liens de preuve pointent vers un domaine de démonstration. Les publications sont réparties sur les dix derniers jours, avec fiches verdict en image, analyses jointes, mentions J'apprécie et commentaires.

## Tests de raisonnement

En plus des preuves, chaque affirmation passe par des tests de raisonnement affichés dans la page Résultat :

| Test | Principe | Effet sur le score |
| --- | --- | --- |
| **Contre-exemple** | Une recherche dédiée (`counter_query`) cherche un cas où l'affirmation ne se vérifie pas. Les affirmations **absolues** (« tous », « aucun », « jamais », « 100 % »…) sont repérées : un seul contre-exemple fiable suffit à les réfuter. | absolue réfutée : plafond 3/10 ; sinon -1 ou -0,5 |
| **Raisonnement par l'absurde** | On suppose l'affirmation vraie, on en déduit 1 ou 2 conséquences nécessaires, recherchées elles aussi, puis confrontées aux preuves. Une conséquence démentie rend l'hypothèse intenable. | -1,5 (démentie par une source fiable), -0,75, ou +0,5 si toutes sont vérifiées |
| **Ordre de grandeur** | Calcul déterministe : valeur annoncée contre statistique officielle la plus récente (FMI, Banque mondiale). | écart d'un facteur 3 ou plus : plafond 3/10 ; ±0,5 |
| **Cohérence interne** | L'énoncé seul se contredit-il (chiffres incompatibles, chronologie impossible) ? | -0,5 |
| **Procédés rhétoriques** | Généralisation hâtive, autorité anonyme, faux dilemme, chiffre sans source… | aucun (information du lecteur) |

Garde-fous : un test ne compte que s'il cite des preuves réellement collectées ([E…], [S…]) ; sinon il est déclaré « non concluant ». L'ajustement total est borné entre -3 et +1 point, et le score avant et après les tests est affiché. Sans LLM, seuls l'ordre de grandeur et le contre-exemple (tiré des preuves qui contredisent) sont calculés.

## Comptes, fil média et back office

- **Premier compte = administrateur.** Au premier lancement, l'écran de connexion propose de créer le compte administrateur ; les analyses existantes lui sont rattachées. Les comptes suivants ont le rôle « personnel média ».
- **Compte lecteur.** À l'inscription, on choisit **Lecteur** ou **Rédaction**. Un lecteur n'a qu'une interface d'actualités : il lit le fil, met des mentions J'apprécie, commente et gère son profil. Il ne peut ni publier, ni analyser, ni consulter les statistiques, l'annuaire, les paramètres ou la vérification physique. Les analyses jointes aux publications lui montrent le score et le verdict, sans la page Résultat. Côté serveur, la règle est appliquée par la dépendance `require_staff` (réponse 403). Un administrateur peut changer le type d'un compte.
- **Données cloisonnées.** Chaque analyse appartient à son auteur, et les préférences (poids, seuils, pays, rétention) sont propres à chaque compte. Une analyse n'est visible par les autres, en lecture seule, que lorsqu'elle est jointe à une publication du fil.
- **Fil média** (`/fil`) : publications avec texte, image (8 Mo max) et analyse jointe ; mentions « J'apprécie », commentaires, modification et suppression par l'auteur, profils publics.
- **Mon espace** (`/espace`) : statistiques personnelles, recherche, filtres par verdict, suivi éditorial (à traiter, en revue, validée, publiée, archivée) et étiquettes, notes internes, publication sur le fil, export CSV.
- **Administration** (`/admin`) : statistiques de la plateforme, changement de rôle, désactivation de compte (sessions fermées aussitôt), masquage ou suppression des publications. Il reste toujours au moins un administrateur actif.

| Variable             | Défaut  | Rôle                                                                 |
| -------------------- | ------- | -------------------------------------------------------------------- |
| `ALLOW_REGISTRATION` | `true`  | `false` ferme les inscriptions (le premier compte reste possible)    |
| `SESSION_DAYS`       | `30`    | Durée de validité d'une session                                      |
| `COOKIE_SECURE`      | `false` | À passer à `true` derrière HTTPS                                     |

## Clés API gratuites

Sans aucune clé, l'application fonctionne en mode dégradé. Wikipedia, GDELT et la Banque mondiale restent actifs, les affirmations sont repérées par heuristique et l'article suit un modèle fixe. Une clé LLM (Gemini ou Groq) change nettement la qualité des résultats.

| Variable                          | Service                 | Rôle                                 | Inscription                                            |
| --------------------------------- | ----------------------- | ------------------------------------ | ------------------------------------------------------ |
| `GEMINI_API_KEY`                  | Gemini (AI Studio)      | Analyse, vision, rédaction           | https://aistudio.google.com/apikey                     |
| `GROQ_API_KEY`                    | Groq                    | Analyse, vision, transcription audio | https://console.groq.com/keys                          |
| `TAVILY_API_KEY`                  | Tavily                  | Recherche web, sites malgaches       | https://app.tavily.com                                 |
| `NEWSDATA_API_KEY`                | NewsData.io             | Presse malgache récente              | https://newsdata.io/register                           |
| `SIGHTENGINE_API_USER` / `SECRET` | Sightengine             | Détection d'images générées          | https://sightengine.com                                |
| `OCR_SPACE_API_KEY`               | OCR.space               | OCR de secours                       | https://ocr.space/ocrapi                               |

La transcription audio nécessite `GROQ_API_KEY`. L'état de chaque service est visible dans la page Paramètres.

## API

| Méthode   | Route                                      | Rôle                                                                         |
| --------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| POST      | `/api/analyses`                            | Lance une analyse (multipart : `text`, `urls` en JSON, `files`) ; répond 202 |
| GET       | `/api/analyses/{id}`                       | État, progression et résultat                                                |
| GET       | `/api/analyses?q=&verdict=&workflow=&tag=` | Analyses du compte connecté                                                  |
| PATCH     | `/api/analyses/{id}`                       | Titre, notes, étiquettes, suivi éditorial                                    |
| GET       | `/api/analyses/stats` · `/export.csv`      | Statistiques et export de l'espace personnel                                 |
| DELETE    | `/api/analyses/{id}`                       | Supprime l'analyse et ses fichiers                                           |
| POST      | `/api/analyses/{id}/article`               | Rédige à nouveau l'article                                                   |
| GET       | `/api/analyses/{id}/article.md` ou `.html` | Export de l'article                                                          |
| GET / PUT | `/api/settings`                            | Préférences du compte                                                        |
| POST      | `/api/auth/register` · `login` · `logout`  | Comptes et sessions ; `GET/PATCH /api/auth/me`, `POST /api/auth/password`    |
| GET/POST  | `/api/posts`                               | Fil (`q`, `author`) ; publication multipart (`body`, `image`, `analysis_id`) |
| PATCH/DEL | `/api/posts/{id}`                          | Modification (auteur), suppression (auteur ou admin)                         |
| PUT/DEL   | `/api/posts/{id}/like`                     | J'apprécie                                                                   |
| GET/POST  | `/api/posts/{id}/comments`                 | Commentaires                                                                 |
| GET       | `/api/users/{id}`                          | Profil public                                                                |
| …         | `/api/admin/stats`, `users`, `posts`       | Administration (rôle admin)                                                  |
| GET       | `/api/health`                              | Mode MCP, outils, services configurés                                        |
| PUT/DEL   | `/api/verifications/location`              | Mobile : partager ou effacer sa position (jamais relue par l'API)            |
| POST/GET  | `/api/verifications`, `/nearby`, `/mine`, `/assigned` | Mobile : demandes de vérification physique                        |
| POST      | `/api/verifications/{id}/accept` · `decline` · `release` · `report` · `cancel` | Mobile : cycle de vie d'une demande          |
| GET/POST  | `/api/verifications/notifications` · `/read` | Mobile : notifications (`undelivered=true` pour le téléphone)            |

## Le serveur MCP

Le backend lance `app/mcp/server.py` au démarrage et l'interroge comme client MCP. Ce serveur peut aussi servir à tout client MCP, par exemple Claude Desktop :

```json
{
  "mcpServers": {
    "hoe-aona-tools": {
      "command": "/chemin/vers/backend/.venv/bin/python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/chemin/vers/backend"
    }
  }
}
```

D'autres serveurs MCP se déclarent dans `backend/mcp_servers.json` ; leurs outils deviennent appelables par `gateway.call(nom_outil, ...)`. Avec `MCP_MODE=direct`, les outils sont appelés sans sous-processus, ce qui est utile pour le débogage.

## Tests

```bash
cd backend
pytest                              # ou : python tests/run_without_pytest.py
```

Les tests couvrent les règles pures : mots-clés et extraits, fiabilité des domaines, signatures IA (IPTC, PNG Stable Diffusion, métadonnées PDF, formules d'assistant) et calcul des scores. `tests/test_accounts.py` vérifie de bout en bout les comptes, le cloisonnement des analyses, le fil, la modération et l'administration. `tests/test_verifications.py` vérifie la vérification physique sur une vraie base PostGIS (`TEST_POSTGIS_URL=postgresql://… pytest`) : rayon de 2 km, attribution unique, renoncement, annulation, effacement des positions.

## À vérifier avant la mise en production

- Le code a été écrit et vérifié sans accès réseau. Les tests unitaires passent, mais les appels réels aux API externes et la compilation Angular doivent être testés une première fois sur votre machine.
- Les quotas gratuits et les noms de modèles (`GEMINI_MODEL`, `GROQ_MODEL`) évoluent : ajustez-les dans `.env`.
- La liste des domaines fiables (`app/services/reliability.py`) gagne à être enrichie avec les médias et institutions de votre pays.
- L'article est marqué « Rédigé par IA, à relire » : une relecture humaine reste nécessaire avant publication.
