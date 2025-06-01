import json
import base64
import logging
from google.cloud import firestore
from datetime import datetime

def determine_device_health(metrics: dict) -> str:
    """Determine device health status based on metrics"""
    score = 0
    
    # CPU usage scoring
    cpu_usage = metrics.get('cpu_usage', 0)
    if cpu_usage > 90:
        score += 3
    elif cpu_usage > 75:
        score += 2
    elif cpu_usage > 50:
        score += 1
    
    # Temperature scoring
    temperature = metrics.get('temperature', 25)
    if temperature > 85:
        score += 3
    elif temperature > 70:
        score += 2
    elif temperature > 60:
        score += 1
    
    # Battery level scoring
    battery_level = metrics.get('battery_level', 100)
    if battery_level < 10:
        score += 3
    elif battery_level < 20:
        score += 2
    elif battery_level < 30:
        score += 1
    
    # Memory usage scoring
    memory_usage = metrics.get('memory_usage', 0)
    if memory_usage > 95:
        score += 2
    elif memory_usage > 85:
        score += 1
    
    # Determine status based on total score
    if score >= 6:
        return 'critical'
    elif score >= 3:
        return 'warning'
    else:
        return 'healthy'

def check_critical_conditions(metrics: dict) -> bool:
    """Check if metrics indicate critical conditions"""
    critical_conditions = [
        metrics.get('temperature', 0) > 85,
        metrics.get('cpu_usage', 0) > 95,
        metrics.get('battery_level', 100) < 5,
        metrics.get('memory_usage', 0) > 98
    ]
    return any(critical_conditions)

def trigger_alert(device_id: str, metrics: dict):
    """Trigger alert for critical conditions"""
    from google.cloud import pubsub_v1
    
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('your-project-id', 'critical-alerts')
    
    alert_data = {
        'device_id': device_id,
        'alert_type': 'critical_condition',
        'metrics': metrics,
        'timestamp': datetime.now().isoformat()
    }
    
    message_data = json.dumps(alert_data).encode('utf-8')
    future = publisher.publish(topic_path, message_data)
    logging.info(f"Published alert for device {device_id}: {future.result()}")

def process_telemetry(event, context):
    """Process IoT telemetry data from Pub/Sub"""
    try:
        # Decode the Pub/Sub message
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        telemetry_data = json.loads(pubsub_message)
        
        # Validate required fields
        required_fields = ['device_id', 'timestamp', 'metrics']
        if not all(field in telemetry_data for field in required_fields):
            logging.error("Missing required fields in telemetry data")
            return
        
        # Initialize Firestore client
        db = firestore.Client()
        
        # Extract data
        device_id = telemetry_data['device_id']
        timestamp = datetime.fromisoformat(telemetry_data['timestamp'])
        metrics = telemetry_data['metrics']
        
        # Check for critical conditions
        if check_critical_conditions(metrics):
            trigger_alert(device_id, metrics)
        
        # Store telemetry in Firestore
        doc_ref = db.collection('telemetry').document()
        doc_ref.set({
            'device_id': device_id,
            'timestamp': timestamp,
            'cpu_usage': metrics.get('cpu_usage', 0),
            'memory_usage': metrics.get('memory_usage', 0),
            'temperature': metrics.get('temperature', 0),
            'battery_level': metrics.get('battery_level', 100),
            'network_quality': metrics.get('network_quality', 'good'),
            'disk_usage': metrics.get('disk_usage', 0),
            'status': determine_device_health(metrics),
            'processed_at': datetime.now()
        })
        
        logging.info(f"Processed telemetry for device {device_id}")
        
    except Exception as e:
        logging.error(f"Error processing telemetry: {str(e)}")
        raise