# Hoe Aona — Functions reference and technical explanation

This document lists the functions of the backend (FastAPI) and the frontend (Angular), then explains in detail the
main function of the project: the analysis pipeline `run_analysis`. The exact scoring rules are also described in
[ANALYSE.md](ANALYSE.md).

---

## Part 1 — Functions

### Backend (`backend/app/`)

#### Core

| File | Functions |
|---|---|
| `main.py` | `lifespan`: starts and stops the MCP gateway and the database with the app. |
| `config.py` | `Settings`, `get_settings` |
| `auth.py` | `hash_password`, `verify_password`, `_token_hash`, `open_session`, `close_session`, `current_token_hash`, `current_user`, `require_admin`, `public_user` |
| `attestation.py` | Signed photo certificates: `_private_key`, `_public_key`, `public_key_pem`, `key_id`, `canonical`, `sign`, `verify`, `sha256_file`, `exif_capture`, `distance_bucket` |
| `schemas.py` | Pydantic models. Analysis: `Preferences`, `InputSummary`, `Evidence`, `Statistic`, `Claim`, `ReasoningTest`, `Criterion`, `Article`, `AnalysisResult`, `AgentEvent`, `AnalysisOut`. Accounts and feed: `UserOut`, `PostOut`, `CommentOut`, `OfficialSourceIn/Out`. Field verification: `VerificationIn/Out`, `ReportOut`, `AttestationOut`. |

**`db.py`, class `Database` (SQLite)**

| Area | Methods |
|---|---|
| Analyses | `create_analysis`, `update_analysis`, `get_analysis`, `list_analyses`, `analysis_stats`, `all_analysis_rows`, `claim_orphan_analyses`, `delete_analysis`, `purge_older_than`, `mark_interrupted` |
| Preferences | `get_preferences`, `save_preferences` |
| Users and sessions | `count_users`, `create_user`, `get_user`, `get_user_by_email`, `update_user`, `list_users`, `count_admins`, `create_session`, `session_user`, `delete_session`, `delete_user_sessions`, `purge_sessions` |
| Feed | `create_post`, `get_post`, `list_posts`, `update_post`, `delete_post`, `is_analysis_published`, `set_like`, `add_comment`, `list_comments`, `get_comment`, `delete_comment`, `platform_stats`, `search_platform_posts` |
| Official sources | `_seed_sources`, `list_sources`, `get_source`, `save_source`, `delete_source` |
| Helpers | `_source_row`, `_row`, `_list_row`, plus the module functions `get_db` and `_now` |

**`geo.py`, class `GeoStore` (PostGIS field verification)**

| Area | Methods |
|---|---|
| Locations | `set_location`, `delete_location`, `location_status`, `purge_locations` |
| Requests | `create_request`, `_notify_nearby`, `get_request`, `is_recipient`, `expire_requests`, `list_nearby`, `list_by_requester`, `list_by_verifier`, `count_open_by_requester`, `accept`, `decline`, `release`, `cancel` |
| Photo capture | `issue_capture_token`, `consume_capture_token`, `distance_to_place` |
| Reports | `has_report`, `list_reports`, `get_report`, `reports_by_hash`, `add_report`, `dispute`, `_exclude_verifier`, `_reopen` |
| Notifications | `_add_notification`, `list_notifications`, `mark_read` |
| Housekeeping | `forget_user`, `_exec`, `_transaction`, `_point` |

#### MCP layer and tools

| File | Functions |
|---|---|
| `mcp/gateway.py` | Class `ToolGateway`: `start`, `stop`, `call`, `_decode`, `mode`, `tool_names`. Also `get_gateway` and `_expand_env`. `call` sends a tool call to an MCP server; if that fails, it calls the Python tool directly. |
| `mcp/server.py` | MCP tools exposed: `wikipedia_search`, `news_search`, `news_madagascar`, `web_search`, `imf_indicator`, `worldbank_indicator`, `fetch_page`, `detect_ai_image` |
| `tools/gdelt.py` | `search`, `_clean_query` |
| `tools/newsdata.py` | `search`, `_query` |
| `tools/tavily.py` | `search` |
| `tools/wikipedia.py` | `search`, `_summary` |
| `tools/worldbank.py` | `indicator`, `guess_country`, `catalog_for_prompt` |
| `tools/imf.py` | `indicator` |
| `tools/webpage.py` | `fetch`, `parse_html`, `_meta`, `_json_ld` |
| `tools/sightengine.py` | `detect_ai_image` |
| `tools/http.py` | `assert_public_url` (SSRF protection), `client`, `error_payload`, `skipped`, `UnsafeURL` |

#### Services (the analysis engine)

| File | Functions |
|---|---|
| `pipeline.py` | **`run_analysis`** (main function), `load_preferences`, `_read_url`, `_remote_image_check`, `_criteria`, `_pct`. Class `Progress`: `__call__`, `advance`, `event`, `finish`, `close_running`, `_flush` |
| `extraction.py` | `extract_text_input`, `extract_file`, `_pdf`, `_docx`, `_html`, `_ocr_space` |
| `ai_detection.py` | `text_signals`, `metadata_signals`, `image_signatures`, `combine`, `noisy_or` |
| `claims.py` | `extract_claims`, `is_universal`, `_heuristic`, `_prompt` |
| `evidence.py` | `gather`, `_tracked`, `_fetch_and_enrich`, `match_contacts`, `_community_candidates`, `_directory_domains`, `_note`, `_gdelt_date` |
| `stance.py` | `evaluate`, `_numeric_stance`, `_valid_refs`, `_prompt`, `_fmt_value` |
| `reasoning.py` | `apply`, `parse_tests`, `fallback_tests`, `magnitude_test`, `parse_number`, `prompt_section`, `_refs`, `_strong`, `_ordered`, `_fmt` |
| `reliability.py` | `assess`, `is_official`, `category_of`, `_lookup`, `_madagascar_entries` |
| `scoring.py` | `claim_truth`, `claim_verdict`, `veracity_score`, `source_score`, `ai_score`, `global_score`, `global_verdict` |
| `article.py` | `generate`, `to_markdown`, `to_html`, `key_points`, `method_section`, `social_post`, `collect_sources`, `sources_markdown`, `_dossier`, `_template`, `_score`, `_inline` |
| `llm.py` | Class `LLMClient`: `chat`, `chat_json`, `describe_image`, `transcribe`, `available`, `_post_chat`. Also `parse_json`, `_providers` |
| `madagascar.py` | `is_madagascar`, `official_domains`, `fold` |
| `textutils.py` | `normalize`, `strip_accents`, `tokens`, `content_tokens`, `keywords`, `split_sentences`, `overlap`, `truncate`, `best_excerpt`, `domain_of`, `numbers_in` |
| `demo_activity.py` | `activity`, `_round` |

#### API routes (`routers/`)

| File | Routes |
|---|---|
| `analyses.py` | `POST /api/analyses`, `GET /api/analyses`, `GET/PATCH/DELETE /api/analyses/{id}`, `GET /stats`, `GET /export.csv`, `POST /{id}/article` (regenerate), `PUT /{id}/article` (edit), `POST /{id}/publish`, `GET /{id}/article.md`, `GET /{id}/article.html` |
| `auth.py` | `/config`, `/register`, `/login`, `/logout`, `/me` (GET, PATCH), `/password` |
| `social.py` | Feed `/posts` (list, create, get, edit, delete, image, like/unlike, comments), `/users/{id}` profile |
| `sources.py` | CRUD for official sources |
| `stats.py` | `/catalog`, `/series`, `/compare`, `/madagascar`, `/activity` |
| `verifications.py` | Location (get, update, stop sharing); requests (create, nearby, mine, assigned, get, accept, decline, release, cancel); capture token, report, dispute, photos; notifications (list, mark read) |
| `attestations.py` | `/public-key`, `/verify`, `/{report_id}` |
| `admin.py` | Stats, users, posts, hiding posts |
| `settings.py` | Read and update settings |
| `system.py` | `/health` |

---

### Frontend (`frontend/src/app/`)

#### Core

| File | Functions |
|---|---|
| `core/api.ts` | Class `Api`, one method per backend route. Analyses: `createAnalysis`, `getAnalysis`, `listAnalyses`, `updateAnalysis`, `analysisStats`, `deleteAnalysis`. Article: `regenerateArticle`, `editArticle`, `publishArticle`, `articleUrl`. Settings: `getSettings`, `saveSettings`, `health`. Accounts: `authConfig`, `me`, `login`, `register`, `logout`, `updateMe`, `changePassword`, `profile`. Feed: `feed`, `createPost`, `editPost`, `deletePost`, `like`, `comments`, `addComment`, `deleteComment`, `getPost`. Sources: `sources`, `createSource`, `updateSource`, `deleteSource`. Statistics: `statsCatalog`, `statsSeries`, `statsCompare`, `statsMadagascar`, `statsActivity`. Admin: `adminStats`, `adminAnalysisStats`, `adminUsers`, `adminUpdateUser`, `adminPosts`, `setHidden`. Plus `errorMessage`. |
| `core/auth.ts` | `ensureLoaded`, `login`, `register`, `logout`, `expire`, `syncLang`, `set`, signals `user` and `isAdmin` |
| `core/format.ts` | Scores: `scoreTone`, `toneColor`, `formatScore`, `pct`, `claimTone`, `stanceTone`, `verdictLabel`, `workflowLabel`. Numbers, files, dates: `formatNumber`, `kindIcon`, `fileSize`, `dayGroup`, `relativeTime`. Avatars: `initials`, `avatarTone` |
| `core/i18n.ts` | `t`, `plural`, `detect`, `applyLang`, `setLang`, pipe `TPipe` |
| `core/markdown.ts` | `escape`, `inline`, markdown pipe |

#### Pages

| Page | Functions |
|---|---|
| `analyze` | Files: `addFiles`, `removeAttachment`, `openPicker`, `pick`, `onPicked`, `onDrop`, `onDragOver`. Links: `addUrl`, `removeUrl`, `hostOf`. Audio: `toggleRecording`, `stopRecording`, `formatSeconds`. Sending: `submit`, `onKeydown`, `focusText` |
| `result` | Loading/navigation: `load` (refreshes every 1.5 s), `toggleDetails`, `scrollTo`, `scrollToArticle`, `anchor`, `back`, `share`. Article: `startEdit`, `patchDraft`, `patchPoints`, `saveArticle`, `openPublish`, `setPublishFormat`, `patchPublish`, `publish`, `copyArticle`, `markdown`, `shortPost`, `regenerate`, `downloadUrl`. Display: `segments`, `sparkline`, `outcomeTone`, `shownTests`, `signed`, `statAge`, `isEstimate`, `tel`, `hideImage`, `flash` |
| `stats` | Loading/selection: `loadSeries`, `loadCompare`, `pick`, `toggleCompare`. Chart: `chart`, `bars`, `niceTicks`, `spark`, `trend`, `onMove`, `onKey`, `tipLeft`. Formatting: `fmt`, `shortUnit`, `age`, `cite`, `fold`, `regionValue` |
| `feed` | `load`, `loadMore`, `onQuery`, `pickImage`, `clearImage`, `clearAnalysis`, `canPublish`, `publish`, `replace`, `drop` |
| `history` | `load`, `loadMore`, `onQuery`, `setVerdict`, `askDelete`, `confirmDelete`, `cancelDelete`, `subtitle`, `statusLabel` |
| `workspace` | Filters: `loadStats`, `load`, `loadMore`, `filters`, `setWorkflow`, `setVerdict`, `setTag`, `resetFilters`. Editing: `edit`, `save`, `quickWorkflow`, `remove`. Display: `count`, `date` |
| `sources` | `load`, `onQuery`, `startNew`, `edit`, `save`, `remove`, `icon`, `host`, `stale`, `copy`, `tel` |
| `settings` | `setUiLanguage`, `share`, `resetWeights`, `save`, `cancel` |
| `profile` | `load`, `startEdit`, `save`, `changePassword` |
| `admin` | `open`, `loadOverview`, `loadUsers`, `loadPosts`, `search`, `setRole`, `toggleActive`, `updateUser` |
| `login` | `submit` |
| `post` | `back` |

#### Shared components

| Component | Functions |
|---|---|
| `agent-progress` | `current`, `elapsed`, `remaining`, `agentName`, `agentIcon`, `onScroll`, `seconds`, `stamp`, `trackEvent` |
| `post-card` | `toggleLike`, `toggleComments`, `sendComment`, `removeComment`, `startEdit`, `saveEdit`, `remove`, `toggleHidden`, `isArticle`, `isLong` |
| `score-ring` | `color`, `label`, `pct`, `marker` |
| `icon` | `svg` |
| `lang-switch` | `choose` |
| `app.ts` (navigation) | `nav`, `secondary`, `secondaryActive`, `moreOpen` |

---

## Part 2 — The main function: `run_analysis(analysis_id)`

File: `backend/app/services/pipeline.py`

### How it is started

1. The user fills the **Analyze** page (text, links, images, documents, audio) and clicks send.
   `AnalyzePage.submit()` calls `Api.createAnalysis()`, which sends a multipart `POST /api/analyses`.
2. The backend saves the uploaded files, creates an analysis row with status `pending`, and schedules
   `run_analysis` with FastAPI `BackgroundTasks`. It answers immediately with the analysis id.
3. The frontend navigates to `/resultat/{id}`. The result page calls `GET /api/analyses/{id}` every 1.5 s
   (rxjs `timer`) while the status is `pending` or `running`. Each response contains `progress`, `step`
   and the `events` journal, displayed by the `agent-progress` component.

### Progress tracking

A `Progress` object writes the percentage and an `AgentEvent` journal to the database. Each event records the
agent, the message, a status (`running` / `done` / `error` / `info`), an optional tool and the elapsed time.
The journal is capped at 200 events.

### The seven steps

| % | Agent | What it does |
|---|---|---|
| 5 → 20 | **Lecteur** (reader) | Turns every input into text. Typed text is used as is. Links go through `fetch_page` (with SSRF protection). PDF and DOCX files are parsed. Images get OCR and metadata reading. Audio is transcribed by the LLM. |
| 20 → 30 | **Détecteur IA** (AI detector) | For each input, estimates the probability that it was AI-generated, combining text style, metadata, image signatures and optionally Sightengine, merged with a noisy-OR. The overall probability is the average weighted by text length; a single input above 0.85 sets the overall value (one generated image is enough). |
| 30 → 45 | **Extracteur** (extractor) | `extract_claims` uses the LLM (or linguistic rules if no LLM is available) to pick out up to `max_claims` checkable claims. For each one it produces a search query, a counter-example query, possible consequences, a World Bank indicator code and a country. |
| 45 → 75 | **Chercheur** (researcher) | `evidence.gather` handles at most 2 claims at a time (a semaphore, to respect free API quotas). For each claim it calls in parallel, through the MCP gateway: Wikipedia, news (GDELT / NewsData), web search (Tavily), the World Bank and the IMF. For Madagascar topics it adds searches on official Malagasy sites and local press. It also runs extra searches for counter-examples and for the claim's consequences. Each source gets a reliability score (`reliability.assess`). |
| 75 → 88 | **Évaluateur** (evaluator) | `stance.evaluate`: the LLM labels each piece of evidence as *supports*, *refutes* or *context*, with a confidence level. Then reasoning tests run: looking for counter-examples, reductio ad absurdum, and order-of-magnitude checks on numbers. |
| 88 → 95 | **Calculateur** (calculator) | Computes the scores (see below). |
| 95 → 100 | **Rédacteur** (writer) | `article.generate` writes the suggested article: verdict in the title, a "key points" box, a section on how the check was done, numbered sources, and a short version for social media. |

At the end, the `AnalysisResult` is saved with status `done`. If an exception occurs, the status becomes `error`,
the events still marked `running` are closed, and the journal is saved so you can see which step failed.

### The scores (`services/scoring.py`)

- **Truth of a claim:** `10 · (S + 0.3) / (S + R + 0.6)`
  - S and R sum `reliability × confidence` for supporting and refuting evidence.
  - An official statistic counts for 0.86.
  - The 0.6 term is a prior: with no evidence, the score stays at 5/10.
  - If the total evidence weight is below 0.35, the claim is *non vérifiable* (not checkable).
  - Verdicts: ≥ 8 *Vrai*, ≥ 6 *Plutôt vrai*, > 4 *Mitigé*, ≥ 2 *Plutôt faux*, otherwise *Faux*.
- **Veracity:** average of the claim scores, weighted by `0.5 + min(evidence weight, 3)`. No claim gives 5/10.
- **Source:** `10 · (0.55 · origin reliability + 0.45 · average reliability of decisive evidence)`.
  Without a known origin, the origin reliability defaults to 0.45.
- **AI:** `10 · (1 − AI probability)`.
- **Overall score:** `source · w₁ + veracity · w₂ + ai · w₃`, with weights chosen by the user in Settings.
  Two hard limits apply:
  - veracity below 4 caps the overall score at 4.4 (false information can never be rated reliable);
  - an AI probability of 0.85 or more caps it at 5.9.
- **Overall verdict:** ≥ 8 *Fiable* (reliable), ≥ 6.5 *Plutôt fiable* (fairly reliable),
  ≥ 4.5 *À vérifier* (to check), otherwise *Douteux* (doubtful).

### Robustness choices

- **No LLM:** every step still runs with heuristics (rule-based claim extraction, numeric stance, template article).
- **MCP failure:** if an MCP server fails, `ToolGateway.call` calls the tool directly in Python.
- **Partial errors:** an unreachable tool or unreadable file adds a warning to the result instead of stopping the analysis.
