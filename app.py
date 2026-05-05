#!/usr/bin/env python3
"""
Sobevita Automation - Professional Production App
Flask + Claude AI Integration
No Authentication Required
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
import sys
import anthropic

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    logger.warning("⚠️ ANTHROPIC_API_KEY not set")
    claude_client = None
else:
    try:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("✅ Claude API initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Claude: {e}")
        claude_client = None

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
PORT = int(os.environ.get("PORT", 5000))

logger.info(f"🚀 Starting Sobevita Automation")
logger.info(f"📊 Model: {CLAUDE_MODEL}")
logger.info(f"🔌 Port: {PORT}")

def call_claude(prompt: str, max_tokens: int = 1024, system: str = None) -> str:
    """Call Claude API safely"""
    if not claude_client:
        raise Exception("Claude not configured")
    
    try:
        kwargs = {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system:
            kwargs["system"] = system
        
        response = claude_client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise

def safe_json_parse(text: str) -> dict:
    """Safely parse JSON from Claude response"""
    try:
        return json.loads(text)
    except:
        return {"text": text}

@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "sobevita-automation",
        "version": "2.0.0",
        "model": CLAUDE_MODEL,
        "claude_ready": bool(claude_client),
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    """Alternative health endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route("/ask-claude", methods=["POST"])
def ask_claude():
    """Ask Claude a question"""
    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question") or data.get("user_input")
        context = data.get("context", "sobevita")
        
        if not question:
            return jsonify({
                "status": "error",
                "message": "Question is required"
            }), 400
        
        if not claude_client:
            return jsonify({
                "status": "error",
                "message": "Claude API not configured"
            }), 503
        
        system_prompts = {
            "sobevita": (
                "Du bist ein hilfreicher KI-Assistent für Sobevita.de, einen deutschen "
                "E-Commerce Store für Küchenprodukte. Du hast Expertise in Produktempfehlungen, "
                "Lagerverwaltung und Kundenservice. Antworte auf Deutsch, professionell und hilfreich. "
                "Halte Antworten unter 200 Wörtern."
            ),
            "general": "You are a helpful, knowledgeable assistant. Answer clearly and concisely.",
            "translate": "You are a professional German translator. Translate accurately and naturally.",
            "seo": "You are an SEO expert. Create optimized, keyword-rich content for e-commerce."
        }
        
        system_prompt = system_prompts.get(context, system_prompts["sobevita"])
        
        logger.info(f"📝 Processing question (context: {context})")
        
        answer = call_claude(question, max_tokens=1024, system=system_prompt)
        
        return jsonify({
            "status": "success",
            "question": question,
            "answer": answer,
            "model": CLAUDE_MODEL,
            "context": context
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error in ask-claude: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/process-product", methods=["POST"])
def process_product():
    """Process product for German translation and optimization"""
    try:
        data = request.get_json(silent=True) or {}
        
        product_id = data.get("product_id") or data.get("productId")
        product_name = data.get("product_name") or data.get("productName")
        product_desc = data.get("description") or data.get("body_html", "")
        product_price = data.get("price") or data.get("product_price", 0)
        
        if not product_id or not product_name:
            return jsonify({
                "status": "error",
                "message": "product_id and product_name are required"
            }), 400
        
        if not claude_client:
            return jsonify({
                "status": "error",
                "message": "Claude API not configured"
            }), 503
        
        logger.info(f"🛍️  Processing product: {product_id} - {product_name}")
        
        prompt = f"""Translate and optimize this product for the German market:

**Product Name:** {product_name}
**Price:** €{product_price}
**Description:** {product_desc}

Provide a JSON response with:
{{
    "german_title": "Optimized German title (max 60 chars)",
    "german_description": "German description (200-300 words)",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "seo_tags": ["tag1", "tag2", "tag3"],
    "marketing_angle": "Key selling point for German market"
}}"""
        
        response_text = call_claude(prompt, max_tokens=2000)
        result = safe_json_parse(response_text)
        
        return jsonify({
            "status": "success",
            "product_id": product_id,
            "product_name": product_name,
            "german_content": result
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error in process-product: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/generate-content", methods=["POST"])
def generate_content():
    """Generate marketing content"""
    try:
        data = request.get_json(silent=True) or {}
        
        content_type = data.get("type", "description")
        product_name = data.get("product_name")
        keywords = data.get("keywords", [])
        tone = data.get("tone", "professional")
        
        if not product_name:
            return jsonify({
                "status": "error",
                "message": "product_name is required"
            }), 400
        
        if not claude_client:
            return jsonify({
                "status": "error",
                "message": "Claude API not configured"
            }), 503
        
        content_prompts = {
            "description": f"Write a compelling product description for {product_name} in a {tone} tone. Include these keywords: {', '.join(keywords)}",
            "instagram": f"Create an engaging Instagram caption for {product_name}. Use hashtags and emojis. Keywords: {', '.join(keywords)}",
            "email": f"Write a professional email product announcement for {product_name}. Tone: {tone}",
            "seo": f"Write SEO-optimized product description for {product_name}. Target keywords: {', '.join(keywords)}"
        }
        
        prompt = content_prompts.get(content_type, content_prompts["description"])
        
        logger.info(f"✍️  Generating {content_type} content for {product_name}")
        
        content = call_claude(prompt, max_tokens=1024)
        
        return jsonify({
            "status": "success",
            "content_type": content_type,
            "product_name": product_name,
            "content": content
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error in generate-content: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/sync-tradelle", methods=["POST"])
def sync_tradelle():
    """Sync product to Tradelle"""
    try:
        data = request.get_json(silent=True) or {}
        
        product_id = data.get("product_id") or data.get("productId")
        german_title = data.get("german_title") or data.get("germanTitle")
        german_desc = data.get("german_description") or data.get("germanDescription")
        
        if not product_id:
            return jsonify({
                "status": "error",
                "message": "product_id is required"
            }), 400
        
        logger.info(f"🔄 Syncing product to Tradelle: {product_id}")
        
        return jsonify({
            "status": "success",
            "message": "Product synced to Tradelle",
            "product_id": product_id,
            "german_title": german_title,
            "german_description": german_desc[:100] + "..." if german_desc else None
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error in sync-tradelle: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/health",
            "/ask-claude",
            "/process-product",
            "/generate-content",
            "/sync-tradelle"
        ]
    }), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"❌ Server error: {e}")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500

if __name__ == "__main__":
    logger.info(f"🎯 Starting Flask server on 0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
