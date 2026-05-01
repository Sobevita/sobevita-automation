from flask import Flask, request, jsonify
import requests
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/process-order', methods=['POST'])
def process_order():
      try:
                data = request.json
                        order_id = data.get('orderId')
                                customer_email = data.get('customerEmail')
                                        order_total = data.get('orderTotal')
                                                products = data.get('products')
                                                        print(f"[{datetime.now()}] Processing order: {order_id}")
                                                                return jsonify({
                                                                            'status': 'success',
                                                                                        'orderId': order_id,
                                                                                                    'processedAt': datetime.now().isoformat()
                                                                                                            }), 200
                                                                                                                except Exception as e:
                                                                                                                        print(f"Error: {str(e)}")
                                                                                                                                return jsonify({'status': 'error', 'message': str(e)}), 500
                                                                                                                                
                                                                                                                                if __name__ == '__main__':
                                                                                                                                    port = int(os.environ.get('PORT', 5000))
                                                                                                                                        app.run(host='0.0.0.0', port=port)
