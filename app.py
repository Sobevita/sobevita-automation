#!/usr/bin/env python3
"""
Sobevita Automation - Flask API for Shopify product content generation
Uses Claude API for German product descriptions and content
"""

from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from anthropic import Anthropic
import json
import sys

# Load environment variables from ~/.sobevita/.env
load_dotenv(os.path.expanduser("~/.sobevita/.env"))

app = Flask(__name__)

# Initialize Anthropic client
try:
    claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
except Exception as e:
    print(f"❌ Failed to initialize Claude: {e}")
    sys.exit(1)

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "sobevita.myshopify.com")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Log startup
print("=" * 70)
print("🚀 SOBEVITA AUTOMATION API - STARTUP")
print("=" * 70)
print(f"Environment: {ENVIRONMENT}")
print(f"Store: {SHOPIFY_STORE}")
print(f"Claude API: ✅ Ready")
print(f"Python: {sys.version.split()[0]}")
print("=" * 70)
print()


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "✅ SYSTEM READY",
        "service": "Sobevita Automation",
        "version": "1.0.0",
        "store": SHOPIFY_STORE
    }), 200


@app.route("/process-product", methods=["POST"])
def process_product():
    """
    Generate German product description using Claude
    
    Expected JSON:
    {
        "product_id": "123456",
        "product_name": "Küchenspritzschutz",
        "product_price": 24.99,
        "product_category": "Kitchen"  (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"status": "❌ ERROR", "message": "No JSON payload provided"}), 400
        
        product_id = data.get("product_id")
        product_name = data.get("product_name", "Unknown")
        product_price = data.get("product_price", 0)
        product_category = data.get("product_category", "General")
        
        if not product_name:
            return jsonify({"status": "❌ ERROR", "message": "product_name is required"}), 400
        
        print(f"\n📦 Processing Product: {product_name} (€{product_price})")
        
        # Create prompt for Claude
        prompt = f"""Du bist ein E-Commerce Content Writer für einen deutschen Shopify Store.
Schreibe eine ansprechende deutsche Produktbeschreibung (150-200 Wörter) für:

Produkt: {product_name}
Preis: €{product_price}
Kategorie: {product_category}

Die Beschreibung soll:
- Überzeugend und customer-focused sein
- Die Vorteile und Features hervorheben
- SEO-optimiert für deutschsprachiges Publikum
- In formales Deutsch geschrieben sein
- Mit "Jetzt bestellen" oder "In den Warenkorb" enden

Antworte NUR mit der Produktbeschreibung, ohne Zusatztext."""

        # Call Claude API
        message = claude.messages.create(
            model="claude-opus-4-20250805",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        description = message.content[0].text
        
        print(f"✅ Generated description ({len(description.split())} words)")
        
        return jsonify({
            "status": "✅ SUCCESS",
            "product_id": product_id,
            "product_name": product_name,
            "product_price": product_price,
            "category": product_category,
            "description": description,
            "tokens_used": {
                "input": message.usage.input_tokens,
                "output": message.usage.output_tokens
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "status": "❌ ERROR", 
            "message": str(e),
            "type": type(e).__name__
        }), 500


@app.route("/batch-process", methods=["POST"])
def batch_process():
    """
    Process multiple products at once
    
    Expected JSON:
    {
        "products": [
            {"product_id": "1", "product_name": "Item 1", "product_price": 10},
            {"product_id": "2", "product_name": "Item 2", "product_price": 20}
        ]
    }
    """
    try:
        data = request.json
        products = data.get("products", [])
        
        if not products:
            return jsonify({"status": "❌ ERROR", "message": "No products provided"}), 400
        
        print(f"\n📦 Batch Processing {len(products)} products...")
        
        results = []
        errors = []
        
        for product in products:
            try:
                product_name = product.get("product_name", "Unknown")
                product_price = product.get("product_price", 0)
                product_id = product.get("product_id")
                
                prompt = f"""Schreibe eine deutsche Produktbeschreibung (100-150 Wörter) für:
Produkt: {product_name}
Preis: €{product_price}

Antworte NUR mit der Beschreibung, kurz und prägnant."""

                message = claude.messages.create(
                    model="claude-opus-4-20250805",
                    max_tokens=800,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                results.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "description": message.content[0].text,
                    "status": "✅ SUCCESS"
                })
                
            except Exception as e:
                errors.append({
                    "product_id": product.get("product_id"),
                    "product_name": product.get("product_name"),
                    "error": str(e)
                })
        
        return jsonify({
            "status": "✅ BATCH COMPLETE",
            "total": len(products),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors if errors else None
        }), 200
        
    except Exception as e:
        return jsonify({"status": "❌ ERROR", "message": str(e)}), 500


@app.route("/health/verbose", methods=["GET"])
def health_verbose():
    """Detailed system health check"""
    return jsonify({
        "status": "✅ READY",
        "api_version": "1.0.0",
        "services": {
            "anthropic": "✅ Connected",
            "flask": "✅ Running"
        },
        "endpoints": {
            "GET /": "Health check",
            "POST /process-product": "Generate single product description",
            "POST /batch-process": "Generate multiple product descriptions",
            "GET /health/verbose": "Detailed status"
        }
    }), 200


if __name__ == "__main__":
    # Run Flask app
    port = int(os.getenv("PORT", 5000))
    debug = ENVIRONMENT == "development"
    
    print(f"\n🚀 Starting app on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}\n")
    
    app.run(debug=debug, host="0.0.0.0", port=port)
