from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from functools import wraps
import os
import json
import anthropic

app = Flask(__name__)
CORS(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

API_KEY = os.environ.get("API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != API_KEY:
            return jsonify(status="error", message="Unauthorized: Invalid or missing API key"), 401
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    return jsonify(
        status="error",
        message=f"Rate limit exceeded: {e.description}. Please try again later."
    ), 429

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@app.route("/health", methods=["GET"])
@limiter.limit("60 per minute")
def health():
    return jsonify(status="healthy"), 200


@app.route("/process-order", methods=["POST"])
@limiter.limit("60 per minute")
def process_order():
    try:
        data = request.get_json()
        order_id = data.get("orderId", "unknown")
        return jsonify(status="success", orderId=order_id), 200
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500


@app.route("/sync-tradelle", methods=["POST"])
@limiter.limit("10 per minute")
@require_api_key
def sync_tradelle():
    try:
        data = request.get_json()
        products = data.get("products", [])

        if not products:
            return jsonify(status="error", message="No products provided"), 400

        product_list = "\n".join(
            f"- {p.get('name', 'Unknown')} | Price: {p.get('price', 'N/A')} | "
            f"Category: {p.get('category', 'N/A')} | Stock: {p.get('stock', 'N/A')}"
            for p in products
        )

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a product data analyst for an e-commerce platform. "
                        "Analyze the following products and return a JSON object with these fields:\n"
                        '- "categories": a dict mapping each unique category to a list of product names in it\n'
                        '- "insights": a list of 2-3 short actionable insights about the product catalog\n'
                        '- "flagged": a list of products that may need attention '
                        "(e.g. missing data, zero stock, unusual pricing)\n\n"
                        f"Products:\n{product_list}\n\n"
                        "Respond with valid JSON only, no extra text."
                    ),
                }
            ],
        )

        raw_text = message.content[0].text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```", 2)[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.rsplit("```", 1)[0].strip()
        analysis = json.loads(raw_text)

        return jsonify(
            status="success", products_synced=len(products), analysis=analysis
        ), 200

    except json.JSONDecodeError:
        return jsonify(
            status="success",
            products_synced=len(products),
            analysis={"raw": message.content[0].text},
        ), 200
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500


@app.route("/ask-claude", methods=["POST"])
@limiter.limit("10 per minute")
@require_api_key
def ask_claude():
    try:
        data = request.get_json()
        question = data.get("question")
        context = data.get("context", "general")

        if not question:
            return jsonify(status="error", message="Question is required"), 400

        system_prompts = {
            "sobevita": "Du bist ein hilfreicher KI-Assistent für Sobevita.de, einen deutschen E-Commerce Store für Küchenprodukte. Du hast Expertise in Produktempfehlungen, Lagerverwaltung und Kundenservice. Antworte auf Deutsch, professionell und hilfreich. Halte Antworten unter 150 Worten.",
            "general": "You are a helpful and knowledgeable assistant. Answer questions clearly and concisely.",
        }

        system_prompt = system_prompts.get(context, system_prompts["general"])

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": question}],
        )

        response_text = message.content[0].text

        return jsonify(
            status="success", question=question, context=context, answer=response_text
        ), 200

    except Exception as e:
        return jsonify(status="error", message=str(e)), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
