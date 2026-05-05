
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from functools import wraps
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import re
import json
import time
import logging
import anthropic
import requests

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("sobevita-automation")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
    headers_enabled=True,
)

API_KEY = os.environ.get("API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "sobevita.myshopify.com")
SHOPIFY_API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2024-01")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

REQUEST_TIMEOUT = (5, 30)
AI_TIMEOUT = 30

if not API_KEY:
    logger.warning("API_KEY env var not set - protected endpoints will reject all requests")

if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY env var not set - AI features will use fallbacks")

if not SHOPIFY_ACCESS_TOKEN:
    logger.warning("SHOPIFY_ACCESS_TOKEN env var not set - Shopify writes will fail")

claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def build_shopify_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[408, 425, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

shopify_session = build_shopify_session()


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = os.environ.get("API_KEY")
        provided = request.headers.get("X-API-Key")

        if not api_key:
            logger.error("API_KEY missing on server")
            return jsonify(status="error", message="Server misconfigured"), 500

        if not provided or provided != api_key:
            logger.warning("Unauthorized request: invalid API key")
            return jsonify(status="error", message="Unauthorized"), 401

        return f(*args, **kwargs)

    return decorated_function
Ctrl + O


    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_KEY:
            logger.error("API_KEY missing on server; rejecting request to %s", request.path)
            return jsonify(
                status="error",
                message="Server misconfigured: API_KEY is missing"
            ), 500

        provided = request.headers.get("X-API-Key")

        if not provided or provided != API_KEY:
            logger.warning(
                "Unauthorized request to %s from %s",
                request.path, get_remote_address()
            )
            return jsonify(
                status="error",
                message="Unauthorized: Invalid or missing API key"
            ), 401

        return f(*args, **kwargs)

    return decorated_function

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    try:
        elapsed = (time.time() - getattr(request, "start_time", time.time())) * 1000
        logger.info(
            "%s %s -> %s %.2fms ip=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed,
            get_remote_address(),
        )
    except Exception as e:
        logger.error("Failed to log request: %s", e)

    return response

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    logger.warning("Rate limit exceeded on %s: %s", request.path, e.description)
    return jsonify(
        status="error",
        message=f"Rate limit exceeded: {e.description}. Please try again later."
    ), 429

@app.errorhandler(404)
def handle_404(e):
    return jsonify(status="error", message="Endpoint not found"), 404

@app.errorhandler(405)
def handle_405(e):
    return jsonify(status="error", message="Method not allowed"), 405

@app.errorhandler(500)
def handle_500(e):
    logger.exception("Internal server error on %s", request.path)
    return jsonify(status="error", message="Internal server error"), 500

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    if isinstance(e, RateLimitExceeded):
        return handle_rate_limit(e)

    logger.exception("Unhandled exception on %s: %s", request.path, e)
    return jsonify(status="error", message="Internal server error"), 500

def safe_json_parse(text):
    if not text or not isinstance(text, str):
        return None

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", cleaned, re.DOTALL)

    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    obj = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if obj:
        try:
            return json.loads(obj.group(0))
        except json.JSONDecodeError:
            pass

    return None

def fallback_german_content(product_name, product_description):
    return {
        "title_de": product_name or "Produkt",
        "description_de": product_description or "Hochwertiges Produkt aus unserem Sortiment.",
    }

def get_german_content(product_name, product_description):
    fallback = fallback_german_content(product_name, product_description)

    if not claude_client:
        logger.error("Claude client not initialized; using fallback content")
        return fallback["title_de"], fallback["description_de"]

    try:
        message = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            timeout=AI_TIMEOUT,
            system=(
                "Du bist ein deutscher Produktschreiber für einen Online-Shop. "
                "Übersetze Produkttitel und Beschreibungen ins Deutsche, natürlich "
                "und verkaufsfördernd. Antworte ausschließlich mit gültigem JSON, "
                "ohne zusätzlichen Text oder Markdown."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Übersetze dieses Produkt ins Deutsche:\n"
                    f"Titel: {product_name}\n"
                    f"Beschreibung: {product_description}\n\n"
                    'Antworte mit JSON Format:\n'
                    '{"title_de": "Deutscher Titel", "description_de": "Deutsche Beschreibung"}'
                )
            }]
        )

        if not message or not message.content:
            logger.error("Empty Claude response; using fallback")
            return fallback["title_de"], fallback["description_de"]

        text = getattr(message.content[0], "text", "") or ""

        parsed = safe_json_parse(text)

        if not isinstance(parsed, dict):
            logger.error("Claude response not parseable as JSON; using fallback. Raw: %s", text[:200])
            return fallback["title_de"], fallback["description_de"]

        title_de = (parsed.get("title_de") or "").strip() or fallback["title_de"]

        description_de = (parsed.get("description_de") or "").strip() or fallback["description_de"]

        return title_de, description_de

    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", e)

    except Exception as e:
        logger.exception("Unexpected error generating German content: %s", e)

    return fallback["title_de"], fallback["description_de"]

def ask_claude_with_fallback(system_prompt, user_content, max_tokens=512):
    if not claude_client:
        logger.error("Claude client not initialized")
        return None

    try:
        message = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            timeout=AI_TIMEOUT,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )

        if not message or not message.content:
            return None

        return getattr(message.content[0], "text", None)

    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", e)

    except Exception as e:
        logger.exception("Unexpected error calling Claude: %s", e)

    return None

def shopify_headers():
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN or "",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def shopify_request(method, path, **kwargs):
    if not SHOPIFY_ACCESS_TOKEN:
        logger.error("SHOPIFY_ACCESS_TOKEN missing; cannot call Shopify")
        return None

    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}{path}"

    kwargs.setdefault("headers", shopify_headers())
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    try:
        response = shopify_session.request(method, url, **kwargs)

        if response.status_code >= 400:
            logger.error(
                "Shopify %s %s -> %s: %s",
                method, path, response.status_code, response.text[:500]
            )

        return response

    except requests.exceptions.Timeout:
        logger.error("Shopify request timed out: %s %s", method, path)

    except requests.exceptions.ConnectionError as e:
        logger.error("Shopify connection error: %s %s -> %s", method, path, e)

    except requests.exceptions.RequestException as e:
        logger.error("Shopify request failed: %s %s -> %s", method, path, e)

    return None

def find_existing_metafield(product_id, namespace, key):
    response = shopify_request(
        "GET",
        f"/products/{product_id}/metafields.json",
        params={"namespace": namespace, "key": key, "limit": 250},
    )

    if not response or response.status_code != 200:
        return None

    try:
        metafields = response.json().get("metafields", [])
    except ValueError:
        logger.error("Invalid JSON response from Shopify metafields list")
        return None

    for mf in metafields:
        if mf.get("namespace") == namespace and mf.get("key") == key:
            return mf

    return None

def upsert_metafield(product_id, namespace, key, value, mf_type):
    existing = find_existing_metafield(product_id, namespace, key)

    if existing and existing.get("id"):
        mf_id = existing["id"]

        payload = {"metafield": {"id": mf_id, "value": value, "type": mf_type}}

        response = shopify_request(
            "PUT",
            f"/metafields/{mf_id}.json",
            json=payload,
        )

        if response and response.status_code in (200, 201):
            logger.info("Updated metafield %s.%s for product %s", namespace, key, product_id)
            return True

        logger.error(
            "Failed to update metafield %s.%s for product %s",
            namespace, key, product_id
        )

        return False

    payload = {
        "metafield": {
            "namespace": namespace,
            "key": key,
            "value": value,
            "type": mf_type,
        }
    }

    response = shopify_request(
        "POST",
        f"/products/{product_id}/metafields.json",
        json=payload,
    )

    if response and response.status_code in (200, 201):
        logger.info("Created metafield %s.%s for product %s", namespace, key, product_id)
        return True

    logger.error(
        "Failed to create metafield %s.%s for product %s",
        namespace, key, product_id
    )

    return False

def merge_product_tags(product_id, new_tags):
    if not new_tags:
        return True

    response = shopify_request("GET", f"/products/{product_id}.json")

    if not response or response.status_code != 200:
        logger.error("Cannot fetch product %s for tag merge", product_id)
        return False

    try:
        product = response.json().get("product", {}) or {}
    except ValueError:
        logger.error("Invalid JSON when fetching product %s", product_id)
        return False

    existing_tags_str = product.get("tags", "") or ""

    existing_tags = [t.strip() for t in existing_tags_str.split(",") if t.strip()]

    merged = list(dict.fromkeys(existing_tags + list(new_tags)))

    if merged == existing_tags:
        return True

    payload = {"product": {"id": product_id, "tags": ",".join(merged)}}

    response = shopify_request("PUT", f"/products/{product_id}.json", json=payload)

    if response and response.status_code in (200, 201):
        logger.info("Merged tags for product %s: %s", product_id, merged)
        return True

    logger.error("Failed to merge tags for product %s", product_id)

    return False

def update_shopify_product(product_id, title_de, description_de, tags=None):
    if not product_id:
        logger.error("update_shopify_product called without product_id")
        return False

    if not SHOPIFY_ACCESS_TOKEN:
        logger.error("Cannot update Shopify product: missing access token")
        return False

    results = []

    if title_de:
        results.append(upsert_metafield(
            product_id, "custom", "title_de", title_de, "single_line_text_field"
        ))

    if description_de:
        results.append(upsert_metafield(
            product_id, "custom", "description_de", description_de, "multi_line_text_field"
        ))

    if tags:
        results.append(upsert_metafield(
            product_id, "custom", "tags", json.dumps(list(tags)), "json"
        ))
        results.append(merge_product_tags(product_id, tags))

    return all(results) if results else True

@app.route("/health", methods=["GET"])
@limiter.limit("120 per minute")
def health():
    return jsonify(
        status="healthy",
        service="sobevita-automation",
        shopify_configured=bool(SHOPIFY_ACCESS_TOKEN),
        ai_configured=bool(claude_client),
    ), 200

@app.route("/process-order", methods=["POST"])
@limiter.limit("30 per minute")
def process_order():
    try:
        data = request.get_json(silent=True) or {}

        product_id = data.get("productId") or data.get("product_id") or data.get("id")

        product_name = data.get("title") or data.get("name") or "Product"

        product_desc = data.get("description") or data.get("body_html") or ""

        if not product_id:
            return jsonify(status="error", message="productId is required"), 400

        logger.info("Processing product %s (%s)", product_id, product_name)

        title_de, description_de = get_german_content(product_name, product_desc)

        tags = ["german-ready", "bilingual"]

        success = update_shopify_product(product_id, title_de, description_de, tags)

        return jsonify(
            status="success" if success else "partial",
            productId=product_id,
            title_de=title_de,
            description_de=description_de,
            tags_added=tags if success else [],
            message="Product updated with German content" if success else "Partial update - check logs"
        ), 200

    except Exception as e:
        logger.exception("Error in /process-order: %s", e)
        return jsonify(status="error", message="Failed to process product"), 500

@app.route("/sync-tradelle", methods=["POST"])
@limiter.limit("10 per minute")
def sync_tradelle():
    try:
        data = request.get_json(silent=True) or {}

        products = data.get("products", [])

        if not isinstance(products, list) or not products:
            return jsonify(status="error", message="No products provided"), 400

        synced_products = []

        for product in products:
            if not isinstance(product, dict):
                continue

            product_id = product.get("id") or product.get("productId")

            product_name = product.get("name") or product.get("title")

            product_desc = product.get("description", "")

            if not product_id or not product_name:
                logger.warning("Skipping product with missing id/name: %s", product)
                continue

            try:
                title_de, description_de = get_german_content(product_name, product_desc)

                tags = ["tradelle-sync", "german-ready"]

                success = update_shopify_product(product_id, title_de, description_de, tags)

            except Exception as inner:
                logger.exception("Error syncing product %s: %s", product_id, inner)

                title_de, description_de, success = "", "", False

            synced_products.append({
                "productId": product_id,
                "name": product_name,
                "title_de": title_de,
                "description_de": description_de,
                "synced": success,
            })

        product_list = "\n".join(
            f"- {p.get('name', 'Unknown')} | German Title: {p.get('title_de', 'N/A')} | Synced: {p.get('synced')}"
            for p in synced_products
        )

        analysis_text = ask_claude_with_fallback(
            system_prompt="You are a product catalog analyst. Always respond with valid JSON only.",
            user_content=(
                "Analyze these German-translated products and provide insights:\n\n"
                f"{product_list}\n\n"
                'Provide JSON response with:\n'
                '{"total_synced": number, "quality_score": 1-10, "recommendations": ["list"]}'
            ),
            max_tokens=512,
        )

        analysis = safe_json_parse(analysis_text) if analysis_text else None

        if not isinstance(analysis, dict):
            analysis = {
                "total_synced": sum(1 for p in synced_products if p["synced"]),
                "quality_score": None,
                "recommendations": [],
                "raw": analysis_text or "AI analysis unavailable",
            }

        return jsonify(
            status="success",
            products_synced=sum(1 for p in synced_products if p["synced"]),
            products_received=len(synced_products),
            products=synced_products,
            analysis=analysis,
        ), 200

    except Exception as e:
        logger.exception("Error in /sync-tradelle: %s", e)
        return jsonify(status="error", message="Failed to sync products"), 500

@app.route("/ask-claude", methods=["POST"])
@limiter.limit("20 per minute")
def ask_claude():
    try:
        data = request.get_json(silent=True) or {}

        question = data.get("question")

        context = data.get("context", "sobevita")

        if not question or not isinstance(question, str):
            return jsonify(status="error", message="Question is required"), 400

        system_prompts = {
            "sobevita": (
                "Du bist ein hilfreicher KI-Assistent für Sobevita.de, einen deutschen "
                "E-Commerce Store für Küchenprodukte. Du hast Expertise in "
                "Produktempfehlungen, Lagerverwaltung und Kundenservice. Antworte auf "
                "Deutsch, professionell und hilfreich. Halte Antworten unter 150 Worten."
            ),
            "general": "You are a helpful and knowledgeable assistant. Answer questions clearly and concisely.",
        }

        system_prompt = system_prompts.get(context, system_prompts["sobevita"])

        answer = ask_claude_with_fallback(
            system_prompt=system_prompt,
            user_content=question,
            max_tokens=512,
        )

        if answer is None:
            return jsonify(
                status="error",
                message="AI service temporarily unavailable",
                question=question,
                context=context,
            ), 503

        return jsonify(
            status="success",
            question=question,
            context=context,
            answer=answer,
        ), 200

    except Exception as e:
        logger.exception("Error in /ask-claude: %s", e)
        return jsonify(status="error", message="Failed to process question"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
