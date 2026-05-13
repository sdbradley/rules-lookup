# Baseball/Softball Rules App — Project Plan

## Context

Build a mobile app that lets users query baseball and softball rules via an LLM chat interface. Rules are sourced from PDF rulebooks (Diamond Youth Baseball, Diamond Youth Softball, and their NFHS references) that are chunked and embedded into a vector database. The app targets Flutter (user is comfortable), Python backend on serverless infrastructure, Firebase Auth, and a freemium subscription model.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Mobile client | Flutter | User is comfortable; strong Firebase SDK |
| Backend API | Python / FastAPI | Best ecosystem for LlamaIndex, Anthropic SDK |
| Containerization | Docker + Docker Compose | Clean local dev environment; Cloud Run consumes Docker images natively |
| Hosting | Google Cloud Run | Serverless, scales to zero, natural fit with Firebase/GCP |
| Auth | Firebase Auth | Excellent Flutter SDK; email + Google sign-in; ties into Firestore for usage tracking |
| Vector DB | Pinecone (managed) | Works with serverless (no embedded DB issues); good free tier for dev |
| Embeddings | Voyage AI (`voyage-3`) | Claude-adjacent; strong retrieval; Anthropic-recommended |
| LLM | Claude (Anthropic API) | Via `claude-sonnet-4-6` for production queries |
| RAG framework | LlamaIndex | Strong PDF readers + structural splitters built in |
| PDF extraction | `pdfplumber` + `pymupdf` fallback | pdfplumber for structured text; pymupdf for scanned/image PDFs |
| Subscription | RevenueCat | Best Flutter + App Store / Play Store integration |
| Usage tracking | Firestore | Natural fit with Firebase ecosystem |

---

## Rulebook Scope (v1)

- Diamond Youth Baseball rulebook
- Diamond Youth Softball rulebook
- NFHS Baseball (referenced by DYB)
- NFHS Softball (referenced by DYS)
- Any additional reference rulebooks cited by the above

All chunks must be tagged with: `source_doc`, `governing_body`, `year`, `rule_number`, `section`, `page_number`.

---

## Architecture Overview

```
Flutter App
  │── Firebase Auth (JWT)
  └── HTTPS → FastAPI (Cloud Run)  ← Docker image pushed to Artifact Registry
               │── Firebase token verification middleware
               │── Firestore (usage tracking / tier check)
               │── Pinecone (vector similarity search)
               └── Anthropic API (Claude generation)

Ingestion Pipeline (offline, run locally via Docker)
  docker-compose run ingestion
  PDF (mounted volume) → pdfplumber → LlamaIndex structural chunker
      → Voyage AI embeddings → Pinecone (with metadata)
```

### Docker Setup

Two containers managed by `docker-compose.yml`:

| Service | Image | Purpose |
|---|---|---|
| `ingestion` | `python:3.12-slim` | PDF extraction + embedding pipeline; PDFs mounted via volume |
| `api` | `python:3.12-slim` | FastAPI backend; same image base as Cloud Run deployment |

Secrets (API keys) passed via `.env` file (gitignored); loaded by Docker Compose.

Local dev flow:
- `docker compose run ingestion` — process PDFs and upsert to Pinecone
- `docker compose up api` — run API locally on port 8000
- Cloud Run deployment: `docker build` + `gcloud run deploy` using the same `api` image

### Freemium Model
- **Free tier**: 5 queries/month (tracked in Firestore per `uid`)
- **Paid tier**: Unlimited queries via RevenueCat in-app subscription
- Backend enforces limits; Flutter app surfaces upgrade prompt

---

## Build Phases

### Phase 0 — Project Scaffolding + Docker Setup
- Create repo with the following structure:
  ```
  /
  ├── ingestion/
  │   ├── Dockerfile
  │   ├── requirements.txt
  │   └── extract.py          ← Phase 1 extraction script lives here
  ├── api/
  │   ├── Dockerfile
  │   └── requirements.txt
  ├── pdfs/                   ← gitignored; mount point for source PDFs
  ├── output/                 ← gitignored; extraction artifacts for inspection
  ├── docker-compose.yml
  └── .env.example
  ```
- `docker-compose.yml` defines `ingestion` and `api` services; both load `.env` for secrets
- `.env.example` documents required variables: `PINECONE_API_KEY`, `VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`, `PINECONE_INDEX_NAME`

### Phase 1 — PDF Sourcing + Extraction Quality ✅
- `pdfplumber` sufficient for all three PDFs — no `pymupdf` fallback needed
- Blank/cover pages flagged correctly by extract.py; no OCR required
- NFHS Softball not available as PDF — converted from HTML via Claude-assisted extraction to structured markdown (see Path B below)
- NFHS Softball markdown validated: 549 nodes, zero articles left as inline bold text, zero structural inconsistencies

**Sources in hand:**
| File | Format | Governing Body |
|---|---|---|
| 2026-DYB-Official-Playing-Rules.pdf | PDF | DYB |
| 2026-DYS-Official-Playing-Rules.pdf | PDF | DYS |
| 2026-official-baseball-rules.pdf | PDF | OBR |
| 2026-NFHS-softball-rules.md | Markdown | NFHS_SOFTBALL |

### Phase 2 — Metadata Schema Design ✅
- `GoverningBody` enum: `DYB`, `DYS`, `OBR`, `NFHS_SOFTBALL`
  - `NFHS_BASEBALL` dropped — DYB uses OBR, not NFHS, as its base ruleset
- `ChunkMetadata` fields: `id`, `text`, `source_doc`, `governing_body`, `year`, `rule_number`, `section_title`, `page_number`, `chunk_index`
- Single Pinecone index with metadata filters (not per-rulebook namespaces)
- Pinecone config: dimension `1024` (voyage-3), metric `cosine`
- `page_number` is `None` for markdown-sourced docs (NFHS Softball)

### Phase 3 — Ingestion Pipeline ✅

Two ingestion paths — same output schema, different input handling:

**Path A — PDF (DYB, DYS, OBR):**
- `pdfplumber` extraction → LlamaIndex `MarkdownNodeParser` (primary) + `SentenceSplitter` (secondary)
- Primary splitter chunks at article/section heading boundaries
- Secondary `SentenceSplitter` (512 token limit) applied only to nodes exceeding ~800 tokens
- Rationale: 6 genuinely long articles in NFHS Softball exceeded 2000 chars; secondary splitter handles without restructuring source

**Path B — Markdown (NFHS Softball):**
- Source is HTML-only; converted via Claude-assisted extraction to structured markdown
- Extraction prompt enforces `#` Rule / `##` Section / `###` Article heading hierarchy
- Same `MarkdownNodeParser` + `SentenceSplitter` pipeline as Path A

**Article number extraction for metadata:**
- NFHS `header_path` format: `/Rule 1 – Field and Equipment/SECTION 1 THE FIELD/`
- Article number parsed from node text prefix (`### ART. 2` → `ART. 2`)
- Combined `rule_number` stored as NFHS-style `1-1-2` (Rule-Section-Article)

Both paths converge at the embedding step: chunks → `voyage-3` → Pinecone with full metadata.

Write a validation script: query each rulebook with 5 known rules and verify top-1 retrieval is correct.

### Phase 4 — CLI Proof-of-Concept ✅
- `query.py`: embed question → Pinecone retrieval (top 5) → Claude generation → answer with citations
- Optional governing body filter via CLI arg: `python query.py "question" DYS`
- **Governing body dependency resolution**: when filtering by `DYS`, Pinecone query uses `$in [DYS, NFHS_SOFTBALL]` so inherited base rules are included
  - `GOVERNING_BODY_DEPS` map defined in `sources.py`; filter built by pure `build_filter()` function in `query.py`
  - DYB, OBR, NFHS_SOFTBALL resolve to themselves only
- Smoke tested: infield fly rule (multi-source, cross-body comparison) and NFHS base distances (filtered, rule 1-1-2(a) cited correctly)

### Phase 5 — FastAPI Backend (Cloud Run) ✅
- Single endpoint: `POST /query`
  - Input: `{ question: str, governing_body?: str }`
  - Auth: Firebase ID token in `Authorization: Bearer` header
  - Checks Firestore for usage count; enforces free tier limit
  - Returns: `{ answer: str, sources: [{ rule_number, section, source_doc, page }] }`
- `POST /query/stream` variant using SSE for streaming responses (better UX)
- Deploy to Cloud Run with `--min-instances=0`

### Phase 6 — Flutter App Shell ✅
- Flutter project setup with Firebase Auth (email + Google sign-in)
- Chat-style UI: message list + text input
- Governing body selector (NFHS Softball, DYB, DYS, OBR, or "All")
- Basic navigation: Home (chat), Settings, Account

### Phase 7 — Flutter ↔ API Integration ✅
- HTTP client to hit Cloud Run API with Firebase ID token
- Stream SSE responses for real-time token display
- Source citation display (expandable chips below each answer showing rule number + section)
- Error handling: rate limit hit → upgrade prompt

### Phase 8 — Freemium Layer ✅
- RevenueCat SDK in Flutter
- Paywall screen: show query count remaining, upgrade CTA
- Backend reads RevenueCat subscription status via webhook → Firestore flag per `uid`
- Free tier enforcement happens in the backend, not the client

### Phase 9 — Prompt Engineering + Multi-Rulebook Disambiguation ✅
- Prompt template that always cites the governing body for each statement
- When chunks from multiple bodies are retrieved: Claude surfaces the differences explicitly ("Under NFHS Baseball, this is X. Diamond Youth Baseball, which references NFHS, applies this as Y.")
- Evaluate on a test set of ~20 questions that span multiple bodies
- **Query logging** (prerequisite for prompt tuning): log each query to Firestore with `uid`, `question`, `governing_body`, retrieved chunk IDs, `answer`, and `latency_ms`. This allows analysis of real user queries without requiring direct feedback and informs prompt tuning decisions.

### Phase 10 — Polish + App Store Prep ✅
- App icon, splash screen ✅
- Privacy policy + terms ✅
- Rate limiting and abuse protection ✅
- TestFlight / Play Console internal testing ✅

### Phase 11 — Per-User Conversation History ✅
Automatic conversation history per user, surfaced like web AI models (ChatGPT, Claude) — no explicit save action required.

**Data model (Firestore):**
```
users/{uid}/conversations/{conversationId}
  - created_at: timestamp
  - governing_body: str | null
  - preview: str  ← first question, truncated, for list display

users/{uid}/conversations/{conversationId}/messages/{messageId}
  - role: "user" | "assistant"
  - content: str
  - created_at: timestamp
  - sources: [{rule_number, section, source_doc, page}]  ← assistant messages only
```

**Backend changes:**
- `POST /query` writes user message + assistant response to Firestore after each successful response
- New conversation created on first message; subsequent messages append to same conversation (frontend passes `conversation_id` or omits for new)
- History writes are fire-and-forget (don't block response streaming)

**Flutter changes:**
- App opens in a fresh chat session by default (no conversation_id yet — one is created on first message)
- History screen: list of past conversations, sorted by recency, showing preview text and date
- Tap conversation → replay message thread (read-only view)
- "New Chat" button in app bar resets to a blank session, same as a fresh app open
- History accessible via icon in app bar or drawer navigation

**Scope:** History is per-user only. No sharing, no export in v1.

### Phase 12 — Shared Question Cache ✅
Cache LLM responses for repeated questions across all users to reduce Anthropic API costs.

**Cache key:** `normalize(question) + "|" + governing_body` where normalization lowercases and strips punctuation. Exact match only — no fuzzy/semantic matching to keep it simple and avoid false hits.

**Data model (Firestore):**
```
question_cache/{cacheKey}
  - question: str          ← original (pre-normalization) for debugging
  - governing_body: str | null
  - answer: str
  - sources: [{rule_number, section, source_doc, page}]
  - hit_count: int
  - created_at: timestamp
  - last_hit_at: timestamp
```

**Backend changes:**
- Before hitting Pinecone + Claude: check `question_cache` for exact key match
- On cache hit: return cached answer immediately (no RAG, no LLM call)
- On cache miss: run normal query pipeline, write result to cache asynchronously
- Cache has no TTL — entries persist until manually cleared (rulebook updates are annual and handled by re-asking)

**Flutter changes:** None — cache is transparent to the client.

**Note:** Exact-match normalization will miss paraphrases and typos. If hit rate proves low after launch, Phase 12 can be revisited with semantic similarity matching using the existing Voyage embeddings infrastructure.

### Phase 13 — Answer Feedback
Thumbs up / thumbs down on each assistant answer, surfaced in the Flutter chat UI. Feeds directly into the existing `query_logs` collection so bad RAG results can be identified without waiting for user complaints.

**Data model:**
- Add `feedback` field to the relevant `query_logs` document: `{ rating: "up" | "down", created_at: timestamp }`

**Backend changes:**
- `POST /feedback` — accepts `{ log_id: str, rating: "up" | "down" }`, writes feedback to the corresponding `query_logs` document
- Auth required; user can only submit feedback for their own queries (verify `uid` matches)

**Flutter changes:**
- Thumbs up / thumbs down buttons below each assistant message
- One tap locks in the rating (tapping again toggles); no free-text comment in v1
- Fire-and-forget HTTP call to `POST /feedback`

### Phase 14 — Share an Answer
Let users share a rule answer as a text snippet — useful for showing an umpire or sending to a teammate mid-game.

**Share format:**
```
[Question]
[Answer]

Sources: [rule_number — section (governing_body)]
—via Rules Lookup
```

**Flutter changes:**
- Share icon button next to each assistant answer
- Uses Flutter's `share_plus` package to invoke the native share sheet (covers iMessage, WhatsApp, copy to clipboard, etc.)
- No backend changes required — share is constructed client-side from the answer and sources already in the chat

### Phase 15 — Follow-up / Multi-Turn Chat
Allow users to ask follow-up questions that carry context from previous turns in the same session. "What about if the runner had already passed second base?" should not require re-typing the full scenario.

**Approach:** Pass the conversation history as additional messages in the Claude API call. Retrieval is re-run on each turn using only the new question (not the full history) so the RAG results stay focused.

**Backend changes:**
- `POST /query` and `POST /query/stream` accept an optional `messages` field: list of `{ role: "user" | "assistant", content: str }` representing prior turns
- Prior messages are prepended to the Claude API call; the system prompt and retrieved chunks remain the same
- History is NOT stored server-side in this phase — the Flutter app owns the session state and sends the full thread each time (keeps the backend stateless)
- Cache bypassed when `messages` is non-empty (multi-turn answers are context-dependent)

**Flutter changes:**
- The in-memory message list already maintained for display is passed back to the API on each subsequent turn
- No UI changes needed beyond what Phase 11 adds

**Note:** This phase overlaps with Phase 11 (conversation history). Phase 11 should be completed first so the message thread is already being stored and displayed.

---

## Key Design Decisions

**Why Pinecone over ChromaDB**: Cloud Run functions are stateless — can't run an embedded DB. Pinecone is a managed service the function connects to over HTTP.

**Why Cloud Run over Lambda**: Firebase Auth + GCP is a natural ecosystem fit; Cloud Run handles Python with a standard `Dockerfile`, no packaging gymnastics.

**Why Voyage over OpenAI embeddings**: Voyage AI is Anthropic-adjacent and consistently benchmarks better on retrieval tasks; `voyage-3` is their current recommended model for production use.

**Why ingestion is offline**: Rulebooks don't change mid-season. The ingestion pipeline is a one-off (or annual) script, not part of the app runtime. This keeps the Cloud Run API simple.

**Why Docker for local dev**: Keeps Python dependencies isolated from the rest of the machine; the `api` Dockerfile is the exact artifact deployed to Cloud Run — no "works on my machine" gap between local and production.

**Why MarkdownNodeParser + SentenceSplitter (not HierarchicalNodeParser)**: Validated against NFHS Softball markdown — `MarkdownNodeParser` produces clean article-level chunks from the `#`/`##`/`###` heading structure. `SentenceSplitter` as a secondary pass handles the handful of genuinely long articles (dead ball conditions, pitching mechanics) without requiring source restructuring.

**Why NFHS Softball is markdown, not PDF**: NFHS no longer distributes free PDFs; rulebook is authenticated web-only. Claude-assisted HTML → markdown extraction preserves rule hierarchy more cleanly than any scraping approach and produces the same heading structure the pipeline expects.

**Why DYB uses OBR, not NFHS**: Diamond Youth Baseball's rule set is OBR-based (essentially MLB rules), not NFHS. `NFHS_BASEBALL` was considered and dropped from the `GoverningBody` enum.

---

## Verification Checklist (per phase)

- [x] Phase 0: `docker compose run ingestion` and `docker compose up api` both start without errors
- [x] Phase 1: Each PDF produces clean, readable text with rule numbers intact; NFHS Softball markdown validated at 549 nodes
- [x] Phase 3: Validation script hits >90% top-1 accuracy on 5 known-answer queries per rulebook
- [x] Phase 4: CLI answers "what is the infield fly rule" correctly with correct source citation
- [x] Phase 5: `POST /query` returns correct answer; rejects expired token; enforces free tier limit
- [x] Phase 7: Flutter app streams a response and displays source chips
- [x] Phase 8: Free user hitting limit sees paywall; paid user does not
- [x] Phase 9: Multi-body question correctly cites both sources
