
from flask import Flask, request, jsonify
from flask_cors import CORS
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


CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

REQUEST_TIMEOUT = (5, 30)
AI_TIMEOUT = 30





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


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        status="healthy",
        service="sobevita-automation",
        ai_configured=bool(claude_client),
    ), 200

@app.route("/process-order", methods=["POST"])
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
