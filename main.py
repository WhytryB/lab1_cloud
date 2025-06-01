from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from google.cloud import firestore
from typing import List, Optional
import asyncio
from datetime import datetime, timedelta

app = FastAPI(title="IoT Monitoring API", version="1.0.0")
security = HTTPBearer()

def authenticate_token(token: str) -> Optional[str]:
    """Authenticate JWT token and return user ID"""
    try:
        # JWT token validation logic
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.JWTError:
        return None

def verify_device_access(user_id: str, device_id: str) -> bool:
    """Verify user has access to specific device"""
    db = firestore.Client()
    device_doc = db.collection('devices').document(device_id).get()
    if device_doc.exists:
        device_data = device_doc.to_dict()
        return device_data.get('owner_id') == user_id
    return False

def get_latest_telemetry(device_id: str) -> dict:
    """Get latest telemetry data for device"""
    db = firestore.Client()
    query = (db.collection('telemetry')
             .where('device_id', '==', device_id)
             .order_by('timestamp', direction=firestore.Query.DESCENDING)
             .limit(1))
    
    docs = list(query.stream())
    if docs:
        return docs[0].to_dict()
    return {}

@app.get("/devices")
async def get_devices(token: str = Depends(security)):
    """Get list of all registered IoT devices"""
    user_id = authenticate_token(token.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = firestore.Client()
    devices = []
    
    docs = db.collection('devices').where('owner_id', '==', user_id).stream()
    
    for doc in docs:
        device_data = doc.to_dict()
        latest_telemetry = get_latest_telemetry(device_data['device_id'])
        
        devices.append({
            'device_id': device_data['device_id'],
            'name': device_data['name'],
            'type': device_data['type'],
            'status': latest_telemetry.get('status', 'unknown'),
            'last_seen': latest_telemetry.get('timestamp'),
            'location': device_data.get('location', 'Unknown')
        })
    
    return devices

@app.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str, 
    hours: Optional[int] = 24,
    token: str = Depends(security)
):
    """Get telemetry data for specific device"""
    user_id = authenticate_token(token.credentials)
    
    if not verify_device_access(user_id, device_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = firestore.Client()
    start_time = datetime.now() - timedelta(hours=hours)
    
    telemetry_query = (db.collection('telemetry')
                      .where('device_id', '==', device_id)
                      .where('timestamp', '>=', start_time)
                      .order_by('timestamp', direction=firestore.Query.DESCENDING)
                      .limit(1000))
    
    telemetry_data = []
    for doc in telemetry_query.stream():
        data = doc.to_dict()
        telemetry_data.append(data)
    
    return telemetry_data

@app.post("/devices/{device_id}/alerts")
async def create_alert_rule(
    device_id: str,
    alert_rule: dict,
    token: str = Depends(security)
):
    """Create new alert rule for device"""
    user_id = authenticate_token(token.credentials)
    
    if not verify_device_access(user_id, device_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = firestore.Client()
    alert_doc = db.collection('alert_rules').document()
    alert_doc.set({
        'device_id': device_id,
        'user_id': user_id,
        'metric': alert_rule['metric'],
        'threshold': alert_rule['threshold'],
        'condition': alert_rule['condition'],
        'enabled': True,
        'created_at': datetime.now()
    })
    
    return {"status": "Alert rule created", "id": alert_doc.id}