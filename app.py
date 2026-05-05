
#!/usr/bin/env python3
"""
Sobevita Automation - Professional Production App
Flask + Claude AI Integration
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
print(f"DEBUG: ANTHROPIC_API_KEY = {ANTHROPIC_API_KEY[:20] if ANTHROPIC_API_KEY else 'NONE'}...")

if not ANTHROPIC_API_KEY:
    logger.warning("⚠️ ANTHROPIC_API_KEY not set")
    claude_client = None
else:
    try:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("✅ Claude API initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Claude: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        claude_client = None

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
PORT = int(os.environ.get("PORT", 8080))

logger.info(f"🚀 Starting Sobevita Automation")
logger.info(f"📊 Model: {CLAUDE_MODEL}")
logger.info(f"🔌 Port: {PORT}")
logger.info(f"✅ Claude Ready: {bool(claude_client)}")

@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "sobevita-automation",
        "version": "2.0.0",
        "model": CLAUDE_MODEL,
        "claude_ready": bool(claude_client),
        "api_key_present": bool(ANTHROPIC_API_KEY)
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    """Alternative health endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route("/ask-claude", methods=["POST"])
def ask_claude():
    """Ask Claude a question"""
    try:
        if not claude_client:
            return jsonify({
                "status": "error",
                "message": "Claude API not configured",
                "debug": {
                    "api_key_present": bool(ANTHROPIC_API_KEY),
                    "client_initialized": bool(claude_client)
                }
            }), 503
        
        data = request.get_json(silent=True) or {}
        question = data.get("question") or data.get("user_input")
        
        if not question:
            return jsonify({
                "status": "error",
                "message": "Question is required"
            }), 400
        
        logger.info(f"📝 Processing question")
        
        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": question}]
        )
        
        answer = response.content[0].text
        
        return jsonify({
            "status": "success",
            "question": question,
            "answer": answer,
            "model": CLAUDE_MODEL
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error in ask-claude: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    logger.info(f"🎯 Starting Flask server on 0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)

