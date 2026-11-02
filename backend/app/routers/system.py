"""État du service : mode MCP, outils disponibles, clés configurées (jamais les clés elles-mêmes)."""
from fastapi import APIRouter

from ..config import get_settings
from ..mcp.gateway import get_gateway
from ..schemas import HealthOut, ProviderStatus

router = APIRouter(prefix="/api", tags=["système"])


@router.get("/health", response_model=HealthOut)
async def health():
    s = get_settings()
    gw = get_gateway()
    providers = [
        ProviderStatus(key="gemini", label="Gemini (Google AI Studio)", role="Analyse, vision et rédaction",
                       configured=bool(s.gemini_api_key), requires_key=True, signup_url="https://aistudio.google.com/apikey"),
        ProviderStatus(key="groq", label="Groq", role="Analyse, vision et transcription audio (Whisper)",
                       configured=bool(s.groq_api_key), requires_key=True, signup_url="https://console.groq.com/keys"),
        ProviderStatus(key="newsdata", label="NewsData.io", role="Presse malgache récente (country=mg)",
                       configured=bool(s.newsdata_api_key), requires_key=True, signup_url="https://newsdata.io/register"),
        ProviderStatus(key="tavily", label="Tavily", role="Recherche web, sites officiels et presse malgaches",
                       configured=bool(s.tavily_api_key), requires_key=True, signup_url="https://app.tavily.com"),
        ProviderStatus(key="sightengine", label="Sightengine", role="Détection d'images générées",
                       configured=bool(s.sightengine_api_user and s.sightengine_api_secret), requires_key=True,
                       signup_url="https://sightengine.com"),
        ProviderStatus(key="ocrspace", label="OCR.space", role="OCR de secours",
                       configured=bool(s.ocr_space_api_key), requires_key=True, signup_url="https://ocr.space/ocrapi"),
        ProviderStatus(key="wikipedia", label="Wikipedia", role="Contexte encyclopédique",
                       configured=True, requires_key=False),
        ProviderStatus(key="gdelt", label="GDELT DOC 2.0", role="Presse mondiale récente",
                       configured=True, requires_key=False),
        ProviderStatus(key="worldbank", label="Banque mondiale", role="Statistiques officielles",
                       configured=True, requires_key=False),
        ProviderStatus(key="imf", label="FMI (World Economic Outlook)", role="Statistiques de l'année en cours",
                       configured=True, requires_key=False),
    ]
    return HealthOut(status="ok", mcp_mode=gw.mode, mcp_tools=gw.tool_names, mcp_errors=gw.errors,
                     providers=providers)
