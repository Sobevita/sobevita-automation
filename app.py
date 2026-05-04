from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='healthy'), 200

@app.route('/process-order', methods=['POST'])
def process_order():
    try:
        data = request.get_json()
        order_id = data.get('orderId', 'unknown')
        return jsonify(status='success', orderId=order_id), 200
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

@app.route('/sync-tradelle', methods=['POST'])
def sync_tradelle():
    try:
        # Get order data
        data = request.get_json()

        # TODO: Call Tradelle API
        # tradelle_api_key = os.environ.get('TRADELLE_API_KEY')
        # products = data.get('products')

        # For now, return success
        return jsonify(status='success', message='Tradelle sync endpoint ready'), 200

    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
