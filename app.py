from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

# Railway webhook endpoint
@app.route('/process-order', methods=['POST'])
def process_order():
        data = request.json

    # Extract Shopify order data
        order_id = data.get('orderId')
        customer_email = data.get('customerEmail')
        order_total = data.get('orderTotal')
        products = data.get('products')

    # Log the order
        print(f"[{datetime.now()}] Order received: {order_id}")

    # TODO: Add Tradelle API call here
        # TODO: Add competitor price check here
        # TODO: Add inventory monitoring here

    return {
                'status': 'success',
                'orderId': order_id,
                'processedAt': datetime.now().isoformat()
    }, 200

if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)
