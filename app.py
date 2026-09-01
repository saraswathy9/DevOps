from flask import Flask, request, jsonify
import boto3
import json
import time

app = Flask(__name__)
s3 = boto3.client('s3', region_name='ap-south-1')
BUCKET_NAME = 'your-iot-data-bucket'

@app.route('/sensor-data', methods=['POST'])
def receive_data():
    data = request.json
    data['timestamp'] = time.time()
    file_name = f"{data['device_id']}_{int(data['timestamp'])}.json"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=json.dumps(data))
    return jsonify({"status": "received"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
