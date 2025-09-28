"""
Health check for localization service
"""
import psutil
from datetime import datetime
from typing import Dict, Any
import asyncio

async def check_database_connection() -> Dict[str, Any]:
    """Check PostgreSQL connection for location data"""
    try:
        from sqlalchemy import create_engine
        from config import DATABASE_URL
        
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM beacons")
            beacon_count = result.fetchone()[0]
            return {
                "status": "healthy",
                "beacons_configured": beacon_count
            }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_influxdb_connection() -> Dict[str, Any]:
    """Check InfluxDB connection for time-series data"""
    try:
        import requests
        import os
        
        influx_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        response = requests.get(f"{influx_url}/health")
        
        if response.status_code == 200:
            return {"status": "healthy"}
        return {"status": "unhealthy", "code": response.status_code}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_trilateration_service() -> Dict[str, Any]:
    """Verify trilateration algorithm is responsive"""
    try:
        # Test with dummy data
        from algorithms.trilateration import calculate_position
        
        test_beacons = [
            {"x": 0, "y": 0, "rssi": -50},
            {"x": 10, "y": 0, "rssi": -60},
            {"x": 5, "y": 10, "rssi": -55}
        ]
        
        position = calculate_position(test_beacons)
        if position:
            return {"status": "healthy", "algorithm": "operational"}
        return {"status": "unhealthy", "algorithm": "failed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def get_health_status() -> Dict[str, Any]:
    """Complete health status for localization service"""
    return {
        "status": "healthy",
        "service": "localization",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": asyncio.run(check_database_connection()),
            "influxdb": asyncio.run(check_influxdb_connection()),
            "trilateration": asyncio.run(check_trilateration_service()),
            "memory": check_memory_usage()
        }
    }

def check_memory_usage() -> Dict[str, Any]:
    """Check memory usage"""
    memory = psutil.virtual_memory()
    return {
        "usage_percent": memory.percent,
        "status": "healthy" if memory.percent < 80 else "warning"
    }