#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import anthropic
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-opus-4-6"
PORT = int(os.getenv("PORT", 8000))

try:
    claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    logger.info("✅ Claude API initialized")
except Exception as e:
    logger.error(f"❌ Failed: {e}")
    claude = None

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "claude_ready": claude is not None,
        "model": CLAUDE_MODEL
    }), 200

@app.route("/ask-claude", methods=["POST"])
def ask_claude():
    try:
        data = request.json
        question = data.get("question") or data.get("user_input", "")
        
        if not question:
            return jsonify({"status": "error", "message": "No question"}), 400

        message = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": question}]
        )
        
        return jsonify({
            "status": "success",
            "question": question,
            "answer": message.content[0].text
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
