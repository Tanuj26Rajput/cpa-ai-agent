# CPA AI Agent

Backend Python project for reviewing shipping and logistics documents, extracting structured shipment data, benchmarking freight costs, detecting anomalies, and generating CPA-friendly reports.

This repo uses a Hermes-managed orchestration layer around a modular agent pipeline. Hermes is used as the planning, extraction, and reporting manager, while Python handles source resolution, document loading, database persistence, Apify calls, and feedback logging.

## Sample Input And Output

### Sample Input

Command:

```bash
python main.py
```

Example input file selected by `main.py`:

```text
data/order_10283.pdf
```

### Sample Output

```text
=== FINAL REPORT ===

# Shipping Cost Review Report

**Source Summary:**
- **Source Type:** Local
- **Source Label:** Local workspace file
- **Document Path:** data\order_10283.pdf

**Document Classification:**
- **Document Type:** Shipping Order
- **Extractor Strategy:** Hermes Structured Extraction
- **Format Confidence:** 95%

**Extracted Shipment Details:**
- **Shipment ID:** 10283
- **Origin:** Barquisimeto, Venezuela
- **Destination:** Not specified
- **Cost:** $1414.80
- **Date:** 2016-08-23
- **Parser:** Hermes Managed

**Duplication/Database Result:**
- **Status:** Duplicate
- **Duplicate Data:** Shipment ID 10283 recorded previously with the same details.

**Historical Average:**
- **Total Shipments Analyzed:** 10
- **Historical Average Cost:** $1271.74

**Current Shipment Cost:**
- **Current Cost:** $1414.80

**Benchmark Rate and Source:**
- **Market Rate:** $825.00
- **Market Source:** Fallback after live Apify
- **Live Apify Status:** Live success but no rate available

**Anomalies:**
- **Anomaly Identified:** Shipment ID 10283 is above the market rate.
  - **Issue:** Current cost of $1414.80 is significantly higher than the market rate of $825.00.

**Conclusion:**
To effectively control shipping costs, it is essential to regularly review shipment data against historical averages and market benchmarks. The current shipment cost exceeds both the historical average and the market rate, indicating potential inefficiencies. Addressing these anomalies and optimizing shipping strategies can lead to better control and reduced costs in future shipments.
```

### How To Read This Output

- `Market Source: Fallback after live Apify` means the Apify actor ran successfully, but the system could not derive a benchmark rate directly from the actor payload, so it used the fallback benchmark heuristic.
- `Live Apify Status: Live success but no rate available` means live marketplace collection worked, even though the benchmark value itself was not parsed from the live payload.
- `Duplicate` means the shipment already exists in `data/shipments.db`.

## Architecture

The system follows this high-level flow:

1. `main.py` parses CLI arguments and chooses the input source.
2. `workflow/pipeline.py` coordinates the end-to-end run.
3. `agents/source.py` resolves the actual document path from local, gdrive-style, or email-style inputs.
4. `agents/loader.py` reads the document into text.
5. `agents/orchestrator.py` asks Hermes to build an execution plan for the document.
6. `agents/classifier.py` converts the Hermes plan into a normalized document classification.
7. `agents/extractor.py` asks Hermes to extract `shipment_id`, `origin`, `destination`, `cost`, and `date`.
8. `agents/dedupe.py` and `doc_db/database.py` save non-duplicate shipment rows into SQLite.
9. `agents/market.py` calls the live Shiply Apify actor, then uses OpenRouter to estimate a benchmark freight rate from the actor output.
10. `agents/analyzer.py` compares the current shipment cost against the benchmark and historical averages.
11. `agents/report.py` asks Hermes to write the final user-facing report.
12. `agents/feedback.py` records pipeline results to a feedback log for later inspection and future improvement loops.

## Entry Point

`main.py` is the CLI entrypoint.

Examples:

```bash
python main.py
python main.py data/order_10248.pdf
python main.py local data/order_10264.pdf
python main.py gdrive C:\path\to\synced\drive\folder
python main.py email C:\path\to\email\drop\folder
```

Behavior:

- If you pass only a file path, it is treated as a local document.
- If you pass `local`, `gdrive`, `email`, or `auto`, the second argument is treated as the source location.
- If no location is passed for `local`, `main.py` selects the first matching sample file from `data/`.

## Orchestration

Hermes is the orchestration manager for the reasoning-heavy parts of the pipeline.

### Hermes-managed steps

- Planning: `agents/orchestrator.py`
- Extraction: `agents/extractor.py`
- Final report writing: `agents/report.py`

### Python-managed steps

- Input/source resolution
- PDF/text loading
- SQLite persistence
- Apify actor calls
- Cost analysis math
- Feedback logging

### Hermes Runner

`agents/hermes_runner.py` is the local bridge into the checked-out `hermes-agent/` repository.

It provides:

- `run_hermes_text_task(prompt, timeout=...)`
- `run_hermes_json_task(prompt, timeout=...)`

Key behavior:

- runs Hermes from the local `hermes-agent/run_agent.py`
- uses `.hermes-runtime/` as the local Hermes home
- tries to parse the `FINAL RESPONSE` block first
- falls back to parsing the raw process output if needed

This makes Hermes output handling more tolerant of banners, summaries, and console chatter.

## Agents

### `agents/source.py`

Source agent for resolving the document input.

Responsibilities:

- local workspace file resolution
- gdrive-style folder ingestion
- email-style `.eml` attachment extraction
- selecting the newest supported file when a directory is provided

Supported suffixes:

- `.pdf`
- `.txt`
- `.md`
- `.eml`

Important note:

- `gdrive` and `email` are practical folder-based ingestion modes, not full Google Drive API / IMAP integrations.

### `agents/loader.py`

Document loader.

Responsibilities:

- load PDF text with `pdfplumber`
- load plain text / markdown files
- reject unsupported file types

Main public functions:

- `load_document(file_path)`
- `load_pdf(file_path)` as a compatibility wrapper

### `agents/orchestrator.py`

Hermes planning agent.

Responsibilities:

- inspect source metadata and document text
- build a structured execution plan
- declare:
  - `document_type`
  - `extractor_strategy`
  - `format_confidence`
  - `required_fields`
  - `analysis_focus`
  - `report_focus`

It also contains a safe `_default_plan()` so the pipeline can continue if Hermes does not return valid JSON during planning.

### `agents/classifier.py`

Classifier adapter.

Responsibilities:

- take the orchestration plan
- normalize it into a simple classification payload used by downstream steps

This is intentionally thin because classification is now Hermes-driven.

### `agents/extractor.py`

Hermes extraction agent.

Responsibilities:

- ask Hermes to extract the canonical shipment fields:
  - `shipment_id`
  - `origin`
  - `destination`
  - `cost`
  - `date`
- normalize nested Hermes outputs into DB-safe scalars

Normalization helpers:

- `_to_text(value)`
- `_to_number(value)`

These exist because Hermes may sometimes return nested JSON for fields such as location or price.

### `agents/dedupe.py`

Dedupe/save agent.

Responsibilities:

- reject extraction payloads already marked as errors
- prevent invalid nested values from reaching SQLite
- insert or detect duplicates via `doc_db/database.py`

Returns:

- `saved`
- `duplicate`
- `error`

### `agents/market.py`

Freight benchmark agent.

Responsibilities:

- call the live Shiply Apify actor
- estimate a benchmark freight rate from the actor output using OpenRouter
- fall back to a route/date heuristic when needed

Live actor:

- actor id: `USU1GjfiedZQLnOBX`

Returned status fields:

- `rate`
- `benchmark_source`
- `apify_actor_status`
- `used_live_apify`

Examples of benchmark source states:

- `apify_openrouter_parsed`
- `fallback_after_live_apify`
- `fallback_no_client`
- `fallback_error`

Examples of actor status states:

- `live_success`
- `live_success_but_no_rate`
- `live_failed`
- `not_initialized`

This separation is important:

- the Apify actor can succeed
- but benchmark extraction from its payload can still fail
- in that case the system uses fallback pricing but still reports that live Apify ran

### `agents/analyzer.py`

Cost analysis agent.

Responsibilities:

- load historical shipment rows from SQLite
- compute historical average cost
- compare current shipment cost against benchmark rate
- flag anomalies when `current_cost > market_rate * 1.3`

Outputs:

- `historical_average_cost`
- `current_cost`
- `market_rate`
- `market_source`
- `apify_actor_status`
- `used_live_apify`
- `anomalies`

### `agents/report.py`

Hermes reporting agent.

Responsibilities:

- ask Hermes to produce the final plain-text CPA-oriented report
- include source, classification, extraction, DB status, averages, benchmark, anomalies, and conclusion

If Hermes report generation fails, the module falls back to a plain Python report summary.

### `agents/feedback.py`

Feedback logging agent.

Responsibilities:

- append one JSON line per run to:
  - `.hermes-runtime/feedback/pipeline_feedback.jsonl`

This is currently a logging loop, not a full automatic self-improvement loop.

## Utilities

### `utils/openrouter_llm.py`

Shared OpenRouter utility.

Responsibilities:

- send prompts to OpenRouter
- use a free model by default:
  - `meta-llama/llama-3.3-8b-instruct:free`
- safely extract the first valid JSON object from model output

Functions:

- `call_openrouter(prompt)`
- `call_openrouter_for_json(prompt)`

### `doc_db/database.py`

SQLite persistence layer.

Responsibilities:

- initialize the `shipments` table
- insert shipments
- fetch historical shipments

Database path:

- `data/shipments.db`

## Workflow Module

### `workflow/pipeline.py`

This is the main coordinator.

Responsibilities:

- initialize the database
- resolve source input
- load document text
- build Hermes execution plan
- classify document from the plan
- extract shipment data
- save/dedupe
- analyze costs and benchmark results
- log feedback
- generate final report

## Environment Variables

Current `.env`-driven dependencies include:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (optional override)
- `APIFY_API_TOKEN`
- `HERMES_MODEL` (optional Hermes model override)
- `GDRIVE_DROP_DIR` (optional)
- `EMAIL_DROP_DIR` (optional)

## External Dependencies

### Hermes Agent

The repo expects a local `hermes-agent/` checkout at the project root.

Used for:

- orchestration
- extraction
- reporting

### OpenRouter

Used for:

- benchmark-rate parsing from Apify actor output

Architecture target:

- OpenRouter is the primary general LLM provider for structured parsing outside the Hermes-managed tasks.

### Apify

Used for:

- live Shiply marketplace scraping

Important distinction:

- Apify actor success does not guarantee benchmark-rate extraction success
- the report now shows both actor status and benchmark source separately

## Output Example

Typical report sections:

- source summary
- document classification
- extracted shipment details
- dedupe/db result
- historical average
- current shipment cost
- benchmark rate
- benchmark source
- Apify actor status
- anomalies
- conclusion

## Current Limitations

The system is a solid prototype, but there are still important caveats:

- Hermes JSON output can still be noisy in some runs, though parsing is more resilient now.
- `gdrive` and `email` are folder-based ingestion modes, not full API integrations.
- feedback is logged, but not yet automatically used to improve prompts or calculators.
- benchmarking uses Shiply marketplace data plus LLM interpretation, not a true FBX/Xeneta feed.
- outbound model/API access can fail depending on machine/network restrictions.

## Install / Dependencies

Current lightweight requirements are listed in `requirementx.txt`.

At minimum, the active Python environment needs support for:

- `pdfplumber`
- `python-dotenv`
- `requests`
- `apify-client`

Hermes itself has its own dependency set in the checked-out `hermes-agent/` project.

## Recommended Next Steps

If you want to make this production-leaning, the best next steps are:

1. replace folder-based `gdrive` and `email` modes with real API integrations
2. add a true feedback-improvement loop instead of logging only
3. make Hermes orchestration more structured with explicit retries on malformed JSON
4. cache successful benchmark results from Apify
5. separate “actor ran live” from “benchmark price was derived live” even more explicitly in UI/reporting
