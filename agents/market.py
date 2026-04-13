import json
import logging
import os
from datetime import datetime

from apify_client import ApifyClient
from dotenv import load_dotenv

from utils.openrouter_llm import call_openrouter_for_json

load_dotenv()
logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
SHIPLY_ACTOR_ID = "USU1GjfiedZQLnOBX"
client = ApifyClient(APIFY_TOKEN) if APIFY_TOKEN else None


def _fallback_rate(document_date=None, route=None):
    base_rate = 1500
    route_text = (route or "").lower()

    if "sweden" in route_text or "northern europe" in route_text:
        base_rate = 800
    elif "france" in route_text or "western europe" in route_text:
        base_rate = 650
    elif "united kingdom" in route_text or "uk" in route_text:
        base_rate = 900

    if document_date:
        try:
            year = datetime.fromisoformat(str(document_date)).year
            if year <= 2017:
                base_rate *= 0.55
            elif year <= 2020:
                base_rate *= 0.8
        except ValueError:
            pass

    return round(base_rate, 2)


def _infer_country(route):
    route_text = (route or "").lower()
    mapping = {
        "sweden": "Sweden",
        "france": "France",
        "united kingdom": "United Kingdom",
        "uk": "United Kingdom",
        "germany": "Germany",
        "netherlands": "Netherlands",
        "belgium": "Belgium",
        "spain": "Spain",
        "italy": "Italy",
        "usa": "United States",
        "united states": "United States",
    }
    for key, value in mapping.items():
        if key in route_text:
            return value
    return "United Kingdom"


def _parse_rate_with_llm(items, country):
    prompt = f"""
You are extracting freight benchmark prices from Shiply marketplace results.

Given the JSON array of marketplace items below, estimate a benchmark market freight rate.

Return exactly one JSON object with these keys:
- rate
- confidence
- reasoning

Rules:
- `rate` must be a JSON number.
- Use only evidence present in the items.
- If several listing prices or budgets exist, estimate a reasonable average market rate.
- If there is not enough usable price information, return `rate` as null.
- Keep reasoning short.

Country:
{country}

Items JSON:
{json.dumps(items[:10], ensure_ascii=False)}
"""
    return call_openrouter_for_json(prompt)


def get_market_rate(route=None, document_date=None):
    """Fetch live Shiply marketplace data and estimate benchmark rate with OpenRouter."""
    fallback_rate = _fallback_rate(document_date=document_date, route=route)

    if client is None:
        return {
            "rate": fallback_rate,
            "benchmark_source": "fallback_no_client",
            "apify_actor_status": "not_initialized",
            "used_live_apify": False,
        }

    run_input = {
        "country": _infer_country(route),
        "maxItems": 10,
        "maxConcurrency": 5,
        "requestDelayMs": 500,
    }

    try:
        run = client.actor(SHIPLY_ACTOR_ID).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        try:
            llm_result = _parse_rate_with_llm(items, run_input["country"])
            parsed_rate = llm_result.get("rate")
        except Exception:
            llm_result = {}
            parsed_rate = None

        if parsed_rate is not None:
            return {
                "rate": round(float(parsed_rate), 2),
                "benchmark_source": "apify_openrouter_parsed",
                "apify_actor_status": "live_success",
                "used_live_apify": True,
                "sample_size": len(items),
                "confidence": llm_result.get("confidence", "medium"),
                "llm_reasoning": llm_result.get("reasoning"),
                "actor_id": SHIPLY_ACTOR_ID,
                "country": run_input["country"],
            }

        return {
            "rate": fallback_rate,
            "benchmark_source": "fallback_after_live_apify",
            "apify_actor_status": "live_success_but_no_rate",
            "used_live_apify": True,
            "actor_id": SHIPLY_ACTOR_ID,
            "country": run_input["country"],
            "item_count": len(items),
        }

    except Exception as exc:
        logger.debug("Apify market lookup failed, using fallback rate: %s", exc)
        return {
            "rate": fallback_rate,
            "benchmark_source": "fallback_error",
            "apify_actor_status": "live_failed",
            "used_live_apify": False,
            "actor_id": SHIPLY_ACTOR_ID,
            "country": run_input["country"],
            "error": str(exc),
        }
