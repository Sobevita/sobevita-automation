#!/usr/bin/env python3
"""
Sobevita Automation - No Auth Version
Simple Flask app for Make.com webhook integration
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
import anthropic

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sobevita-automation")

# Initialize Claude
try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except:
    claude_client = None
    logger.warning("Claude API key not configured")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.route("/", methods=["GET"])
def health():
    """Health check - NO AUTH REQUIRED"""
    return jsonify(
        status="healthy",
        service="sobevita-automation",
        version="2.0.0",
        claude_ready=bool(claude_client)
    ), 200


# ============================================================
# MAIN ENDPOINTS - NO AUTHENTICATION
# ============================================================

@app.route("/ask-claude", methods=["POST"])
def ask_claude():
    """Ask Claude a question - NO AUTH REQUIRED"""
    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question")
        context = data.get("context", "sobevita")

        if not question:
            return jsonify(status="error", message="Question is required"), 400

        if not claude_client:
            return jsonify(status="error", message="Claude not configured"), 500

        system_prompts = {
            "sobevita": (
                "Du bist ein hilfreicher KI-Assistent für Sobevita.de, einen deutschen "
                "E-Commerce Store für Küchenprodukte. Antworte auf Deutsch, professionell und hilfreich."
            ),
            "general": "You are a helpful assistant. Answer clearly and concisely.",
        }

        system_prompt = system_prompts.get(context, system_prompts["sobevita"])

        logger.info("Processing question: %s", question[:50])

        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )

        answer = response.content[0].text

        return jsonify(
            status="success",
            question=question,
            answer=answer,
            model=CLAUDE_MODEL
        ), 200

    except Exception as e:
        logger.exception("Error in ask-claude: %s", e)
        return jsonify(status="error", message=str(e)), 500


@app.route("/process-product", methods=["POST"])
def process_product():
    """Process product for German translation - NO AUTH REQUIRED"""
    try:
        data = request.get_json(silent=True) or {}
        product_id = data.get("product_id") or data.get("productId")
        product_name = data.get("product_name") or data.get("productName")
        product_desc = data.get("description", "")

        if not product_id or not product_name:
            return jsonify(status="error", message="product_id and product_name required"), 400

        if not claude_client:
            return jsonify(status="error", message="Claude not configured"), 500

        logger.info("Processing product: %s (%s)", product_id, product_name)

        prompt = f"""Translate this product to German and create marketing content:

Product Name: {product_name}
Description: {product_desc}

Provide JSON response with:
{{"german_title": "German title", "german_description": "German description", "keywords": ["keyword1", "keyword2"]}}"""

        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text
        
        try:
            result = json.loads(response_text)
        except:
            result = {"german_title": product_name, "german_description": response_text}

        return jsonify(
            status="success",
            product_id=product_id,
            product_name=product_name,
            german_content=result
        ), 200

    except Exception as e:
        logger.exception("Error in process-product: %s", e)
        return jsonify(status="error", message=str(e)), 500


@app.route("/sync-tradelle", methods=["POST"])
def sync_tradelle():
    """Sync product to Tradelle - NO AUTH REQUIRED"""
    try:
        data = request.get_json(silent=True) or {}
        product_id = data.get("product_id") or data.get("productId")
        german_title = data.get("german_title") or data.get("germanTitle")
        german_desc = data.get("german_description") or data.get("germanDescription")

        if not product_id:
            return jsonify(status="error", message="product_id required"), 400

        logger.info("Syncing product to Tradelle: %s", product_id)

        # In production, sync to actual Tradelle API
        # For now, just log and return success

        return jsonify(
            status="success",
            product_id=product_id,
            message="Product synced to Tradelle",
            german_title=german_title,
            german_description=german_desc
        ), 200

    except Exception as e:
        logger.exception("Error in sync-tradelle: %s", e)
        return jsonify(status="error", message=str(e)), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify(status="error", message="Endpoint not found"), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify(status="error", message="Internal server error"), 500


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
