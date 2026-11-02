"""Rédaction d'un article de vérification prêt à publier.

Le LLM ne reçoit que les affirmations, verdicts, arguments et sources retenues, numérotées
[1], [2]… Sans LLM, un modèle déterministe produit un article sobre et complet.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone

from ..schemas import AnalysisResult, Article, ArticleSource
from .llm import LLMClient
from .stance import _fmt_value
from .textutils import truncate

log = logging.getLogger("hoe-aona.article")

LANG_NAMES = {"fr": "français", "en": "anglais", "mg": "malgache"}

SYSTEM = (
    "Tu es secrétaire de rédaction d'un service de fact-checking. Tu écris des articles exacts, neutres, "
    "pédagogiques, sans jamais ajouter un fait absent du dossier fourni. Réponds en JSON valide."
)


def collect_sources(result: AnalysisResult) -> tuple[list[ArticleSource], dict[str, int]]:
    """Numérote les sources décisives d'abord, puis le contexte ; renvoie aussi la table preuve -> numéro."""
    sources: list[ArticleSource] = []
    index: dict[str, int] = {}
    url_to_n: dict[str, int] = {}

    def add(key: str, title: str, publisher: str, url: str) -> None:
        if url not in url_to_n:
            url_to_n[url] = len(sources) + 1
            sources.append(ArticleSource(n=url_to_n[url], title=title, publisher=publisher, url=url))
        index[key] = url_to_n[url]

    for decisive in (True, False):
        for claim in result.claims:
            for e in claim.evidence:
                if (e.stance != "context") == decisive:
                    add(f"{claim.id}:{e.id}", e.title, e.publisher, e.url)
            for s in claim.statistics:
                if (s.stance != "context") == decisive:
                    add(f"{claim.id}:{s.id}", f"{s.indicator_name}, {s.country}", s.source_name, s.source_url)
    return sources[:15], index


def _dossier(result: AnalysisResult, index: dict[str, int]) -> str:
    def renumber(text: str, claim_id: str) -> str:
        return re.sub(r"\[([ES]\d+)\]", lambda m: f"[{index.get(f'{claim_id}:{m.group(1)}', '?')}]", text)

    parts = [f"Sujet : {result.topic or 'non précisé'}",
             f"Résumé du contenu analysé : {result.summary}",
             f"Score global : {result.global_score}/10 ({result.verdict_label})"]
    for c in result.criteria:
        parts.append(f"Critère {c.label} : {c.score}/10 — {c.summary}")
    for claim in result.claims:
        parts.append(f"\nAffirmation : « {claim.text} » → {claim.verdict_label} ({claim.truth_score}/10)")
        parts.append(f"Conclusion : {renumber(claim.conclusion, claim.id)}")
        for a in claim.arguments_for:
            parts.append(f"  + {renumber(a, claim.id)}")
        for a in claim.arguments_against:
            parts.append(f"  − {renumber(a, claim.id)}")
        for s in claim.statistics:
            n = index.get(f"{claim.id}:{s.id}")
            parts.append(f"  Chiffre officiel [{n}] : {s.indicator_name}, {s.country} = {_fmt_value(s.latest_value)} {s.unit}"
                         f" en {s.latest_year} (base mise à jour le {s.last_updated or 'n.d.'}). {s.comment}")
        for e in claim.evidence:
            n = index.get(f"{claim.id}:{e.id}")
            parts.append(f"  Source [{n}] {e.publisher}, {e.published_at or 'date inconnue'} : « {truncate(e.excerpt, 260)} » ({e.stance})")
        for test in claim.reasoning:
            if test.outcome != "non_concluant" and test.kind != "sophisme":
                parts.append(f"  Test « {test.label} » : {test.outcome} — {renumber(test.summary, claim.id)}")
    if result.excluded_sources:
        parts.append(f"\n{len(result.excluded_sources)} source(s) écartée(s) car probablement générées par IA ou peu fiables.")
    return "\n".join(parts)


TOOL_LABELS = {
    "wikipedia_search": "Wikipedia", "news_search": "la presse internationale (GDELT)", "web_search": "le web",
    "news_madagascar": "la presse malgache", "worldbank_indicator": "la Banque mondiale", "imf_indicator": "le FMI",
    "fetch_page": "les pages citées", "detect_ai_image": "un détecteur d'images générées",
    "platform_posts": "les publications du fil média",
}


def _score(value: float) -> str:
    return str(value).replace(".", ",")


def key_points(result: AnalysisResult) -> list[str]:
    points = [f"« {truncate(c.text, 110)} » : {c.verdict_label.lower()} ({_score(c.truth_score)}/10)."
              for c in result.claims[:3]]
    ai = next((c for c in result.criteria if c.key == "ai"), None)
    if ai:
        points.append(ai.summary.rstrip(".") + ".")
    return points[:4]


def method_section(result: AnalysisResult, sources: list[ArticleSource]) -> str:
    consulted = [TOOL_LABELS[t] for t in result.tools_used if t in TOOL_LABELS]
    tests = sum(1 for c in result.claims for t in c.reasoning if t.outcome != "non_concluant")
    parts = [f"Nous avons isolé {len(result.claims)} affirmation(s) vérifiable(s) et retenu {len(sources)} source(s)"
             + (f", après avoir consulté {', '.join(consulted)}" if consulted else "") + "."]
    if tests:
        parts.append(f"{tests} test(s) de raisonnement (contre-exemples, conséquences par l'absurde, ordres de grandeur) "
                     "ont complété la recherche de preuves.")
    if result.excluded_sources:
        parts.append(f"{len(result.excluded_sources)} source(s) ont été écartées car jugées peu fiables "
                     "ou probablement générées par IA.")
    return " ".join(parts)


def social_post(result: AnalysisResult, title: str, lead: str) -> str:
    """Texte court suggéré pour le fil média : verdict, éléments clés, invitation à lire l'analyse."""
    lines = [f"🔎 {title}", "", lead, ""]
    for c in result.claims[:3]:
        lines.append(f"• {truncate(c.text, 90)} → {c.verdict_label}")
    lines += ["", f"Score de fiabilité : {_score(result.global_score)}/10 ({result.verdict_label.lower()}). "
                  "Preuves et sources dans l'analyse jointe."]
    return truncate("\n".join(lines), 900)


def _template(result: AnalysisResult, sources: list[ArticleSource], index: dict[str, int]) -> tuple[str, str, str]:
    def renumber(text: str, claim_id: str) -> str:
        return re.sub(r"\[([ES]\d+)\]", lambda m: f"[{index.get(f'{claim_id}:{m.group(1)}', '?')}]", text)

    title = f"Vérification : {result.topic or 'ce qui circule'} — {result.verdict_label.lower()}"
    lead = (f"Après examen de {len(result.claims)} affirmation(s) et de {len(sources)} source(s), "
            f"le contenu obtient un score de fiabilité de {_score(result.global_score)}/10.")
    body = ["## Ce qui circule", result.summary or "Un contenu a été soumis à vérification.", "", "## Ce que disent les faits"]
    for claim in result.claims:
        body.append(f"### « {claim.text} »")
        body.append(f"**Verdict : {claim.verdict_label}.** {renumber(claim.conclusion, claim.id)}")
        for a in claim.arguments_for + claim.arguments_against:
            body.append(f"- {renumber(a, claim.id)}")
        for test in claim.reasoning:
            if test.outcome in ("refute", "affaiblit", "compatible") and test.kind != "sophisme" and test.summary:
                body.append(f"- *{test.label}* : {renumber(test.summary, claim.id)}")
        body.append("")
    stats = [(c, s) for c in result.claims for s in c.statistics]
    if stats:
        body.append("## Les chiffres officiels")
        for c, s in stats:
            body.append(f"- {s.indicator_name}, {s.country} : {_fmt_value(s.latest_value)} {s.unit} en {s.latest_year} "
                        f"[{index.get(f'{c.id}:{s.id}', '?')}]. {s.comment}")
        body.append("")
    ai = next((c for c in result.criteria if c.key == "ai"), None)
    if ai:
        body += ["## Le contenu a-t-il été généré par IA ?", ai.summary, ""]
    body += ["## Comment nous avons vérifié", method_section(result, sources), ""]
    body += ["## Notre verdict", f"{result.verdict_label} ({_score(result.global_score)}/10)."]
    return title, lead, "\n".join(body)


def sources_markdown(sources: list[ArticleSource]) -> str:
    return "\n".join(f"{s.n}. [{s.title}]({s.url}) — {s.publisher}" for s in sources)


async def generate(result: AnalysisResult, llm: LLMClient, lang: str, warnings: list[str]) -> Article:
    sources, index = collect_sources(result)
    now = datetime.now(timezone.utc)
    if llm.available and result.claims:
        prompt = f"""Rédige en {LANG_NAMES.get(lang, 'français')} un article de vérification prêt à publier (500 à 800 mots)
à partir de ce dossier. Il sera proposé comme suggestion à un journaliste qui le relira avant publication.

Exigences de qualité :
- titre informatif qui donne le verdict (pas de question, pas de clic facile), 90 caractères max ;
- chapô de 2 phrases : ce qui circule, puis ce que montre la vérification ;
- n'utilise que les faits du dossier, chacun suivi de son numéro de source entre crochets, ex. [2] ;
- reformule, ne recopie pas les extraits (au plus une courte citation entre guillemets) ;
- donne chaque chiffre avec son année et sa source ; signale quand une donnée officielle date de plus d'un an
  ou qu'il s'agit d'une estimation ; explique ce que le chiffre signifie concrètement pour le lecteur ;
- distingue clairement ce qui est établi, ce qui est contredit et ce qui reste non vérifiable ;
- si le sujet concerne Madagascar, donne le contexte local utile (institution compétente, région concernée) ;
- phrases courtes, vocabulaire accessible, ton neutre, aucun sensationnalisme, aucun jugement sur les personnes ;
- structure en Markdown : ## Ce qui circule, ## Ce que disent les faits (un ### par affirmation, avec son verdict en gras),
  ## Les chiffres (si pertinent), ## Le contenu a-t-il été généré par IA ?, ## Comment nous avons vérifié, ## Notre verdict ;
- pas de liste de sources (elle est ajoutée automatiquement).

Ajoute aussi :
- "key_points" : 3 ou 4 phrases très courtes résumant l'essentiel (verdicts et chiffre clé) ;
- "social_post" : une publication de 400 à 700 caractères pour un fil d'actualité professionnel, qui annonce le verdict,
  cite l'élément décisif et invite à consulter l'analyse ; un seul emoji en tête au plus, pas de hashtag.

DOSSIER :
{_dossier(result, index)}

JSON attendu : {{"title": "...", "lead": "...", "key_points": ["..."], "body_markdown": "...",
"social_post": "...", "tags": ["3 à 5 mots-clés"]}}"""
        try:
            data = await llm.chat_json(SYSTEM, prompt, max_tokens=6000)
            if data.get("body_markdown"):
                body = re.sub(r"\[(\d+)\]", lambda m: m.group(0) if int(m.group(1)) <= len(sources) else "", data["body_markdown"])
                title = truncate(data.get("title", ""), 140) or "Vérification"
                lead = truncate(data.get("lead", ""), 400)
                points = [truncate(str(p), 200) for p in data.get("key_points", []) if str(p).strip()][:4]
                post = truncate(str(data.get("social_post", "")).strip(), 1200)
                return Article(title=title, lead=lead, body_markdown=body.strip(),
                               key_points=points or key_points(result),
                               social_post=post or social_post(result, title, lead),
                               tags=[str(t) for t in data.get("tags", [])][:6], sources=sources,
                               generated_by="llm", generated_at=now)
        except Exception as exc:  # noqa: BLE001
            log.warning("Rédaction LLM échouée : %s", exc)
            warnings.append("Rédaction par LLM indisponible : article produit à partir du modèle")
    title, lead, body = _template(result, sources, index)
    return Article(title=title, lead=lead, body_markdown=body, tags=[result.topic] if result.topic else [],
                   key_points=key_points(result), social_post=social_post(result, title, lead),
                   sources=sources, generated_by="modele", generated_at=now)


def to_markdown(article: Article) -> str:
    essentials = ("## L'essentiel\n\n" + "\n".join(f"- {p}" for p in article.key_points) + "\n\n") \
        if article.key_points else ""
    return (f"# {article.title}\n\n*{article.lead}*\n\n{essentials}{article.body_markdown}\n\n## Sources\n\n"
            f"{sources_markdown(article.sources)}\n")


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', text)


def to_html(article: Article, lang: str = "fr") -> str:
    out, in_list = [], None
    for line in to_markdown(article).splitlines():
        m_head = re.match(r"^(#{1,3}) (.*)", line)
        m_item = re.match(r"^(?:- |(\d+)\. )(.*)", line)
        if in_list and not m_item:
            out.append(f"</{in_list}>")
            in_list = None
        if m_head:
            level = len(m_head.group(1))
            out.append(f"<h{level}>{_inline(m_head.group(2))}</h{level}>")
        elif m_item:
            tag = "ol" if m_item.group(1) else "ul"
            if in_list != tag:
                if in_list:
                    out.append(f"</{in_list}>")
                out.append(f"<{tag}>")
                in_list = tag
            out.append(f"<li>{_inline(m_item.group(2))}</li>")
        elif line.strip():
            out.append(f"<p>{_inline(line)}</p>")
    if in_list:
        out.append(f"</{in_list}>")
    return (f"<!DOCTYPE html><html lang=\"{html.escape(lang)}\"><head><meta charset=\"utf-8\"><title>"
            f"{html.escape(article.title)}</title></head><body><article>{''.join(out)}</article></body></html>")
