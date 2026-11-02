# Hoe Aona

Application web responsive d'analyse de la désinformation. Elle reçoit un texte, une image, un document, un audio ou des liens. Elle repère les affirmations vérifiables et cherche des preuves auprès de sources fiables via un serveur MCP. Elle écarte les sources générées par IA, puis donne trois scores sur 10 (source, véracité des données, part d'IA) et un score global. Chaque argument renvoie à une preuve (lien, extrait, image, statistique datée), et un article prêt à publier est proposé.

L'analyse du besoin, la méthode de calcul et les limites sont décrites dans [docs/ANALYSE.md](docs/ANALYSE.md).

## Architecture

```
frontend/   Angular 20 (composants autonomes, signals) : Analyser, Résultat, Historique, Paramètres
backend/    FastAPI
  app/mcp/server.py     serveur MCP « Hoe aona?-tools » (FastMCP, stdio)
  app/mcp/gateway.py    client MCP utilisé par le pipeline
  app/tools/            Fact Check, Wikipedia, GDELT, Tavily, Banque mondiale, lecture de page, Sightengine
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

## Clés API gratuites

Sans aucune clé, l'application fonctionne en mode dégradé. Wikipedia, GDELT et la Banque mondiale restent actifs, les affirmations sont repérées par heuristique et l'article suit un modèle fixe. Une clé LLM (Gemini ou Groq) change nettement la qualité des résultats.

| Variable | Service | Rôle | Inscription |
|---|---|---|---|
| `GEMINI_API_KEY` | Gemini (AI Studio) | Analyse, vision, rédaction | https://aistudio.google.com/apikey |
| `GROQ_API_KEY` | Groq | Analyse, vision, transcription audio | https://console.groq.com/keys |
| `GOOGLE_FACTCHECK_API_KEY` | Google Fact Check Tools | Fact-checks publiés | Console Google Cloud, activer « Fact Check Tools API » |
| `TAVILY_API_KEY` | Tavily | Recherche web | https://app.tavily.com |
| `SIGHTENGINE_API_USER` / `SECRET` | Sightengine | Détection d'images générées | https://sightengine.com |
| `OCR_SPACE_API_KEY` | OCR.space | OCR de secours | https://ocr.space/ocrapi |

La transcription audio nécessite `GROQ_API_KEY`. L'état de chaque service est visible dans la page Paramètres.

## API

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/analyses` | Lance une analyse (multipart : `text`, `urls` en JSON, `files`) ; répond 202 |
| GET | `/api/analyses/{id}` | État, progression et résultat |
| GET | `/api/analyses?q=&verdict=&limit=&offset=` | Historique |
| DELETE | `/api/analyses/{id}` | Supprime l'analyse et ses fichiers |
| POST | `/api/analyses/{id}/article` | Rédige à nouveau l'article |
| GET | `/api/analyses/{id}/article.md` ou `.html` | Export de l'article |
| GET / PUT | `/api/settings` | Préférences |
| GET | `/api/health` | Mode MCP, outils, services configurés |

## Le serveur MCP

Le backend lance `app/mcp/server.py` au démarrage et l'interroge comme client MCP. Ce serveur peut aussi servir à tout client MCP, par exemple Claude Desktop :

```json
{
  "mcpServers": {
    "Hoe aona?-tools": {
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

Les tests couvrent les règles pures : mots-clés et extraits, fiabilité des domaines, signatures IA (IPTC, PNG Stable Diffusion, métadonnées PDF, formules d'assistant) et calcul des scores.

## À vérifier avant la mise en production

- Le code a été écrit et vérifié sans accès réseau. Les tests unitaires passent, mais les appels réels aux API externes et la compilation Angular doivent être testés une première fois sur votre machine.
- Les quotas gratuits et les noms de modèles (`GEMINI_MODEL`, `GROQ_MODEL`) évoluent : ajustez-les dans `.env`.
- La liste des domaines fiables (`app/services/reliability.py`) gagne à être enrichie avec les médias et institutions de votre pays.
- L'article est marqué « Rédigé par IA, à relire » : une relecture humaine reste nécessaire avant publication.
