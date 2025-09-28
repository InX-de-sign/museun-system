"""
iBeacon scanner module for Raspberry Pi
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from bleak import BleakScanner

logger = logging.getLogger(__name__)

class BeaconScanner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.known_beacons = {b['uuid']: b for b in config.get('beacons', [])}
        self.scanner = None
        
    async def scan(self) -> List[Dict[str, Any]]:
        """Scan for iBeacons and return readings"""
        readings = []
        
        try:
            devices = await BleakScanner.discover(
                timeout=self.config['scan_duration']
            )
            
            for device in devices:
                if self._is_ibeacon(device):
                    beacon_data = self._parse_ibeacon(device)
                    if beacon_data['uuid'] in self.known_beacons:
                        readings.append({
                            'beacon_id': beacon_data['uuid'],
                            'rssi': device.rssi,
                            'timestamp': datetime.utcnow().isoformat(),
                            'location': self.known_beacons[beacon_data['uuid']]['location']
                        })
                        
        except Exception as e:
            logger.error(f"Beacon scan error: {e}")
            
        return readings
    
    def _is_ibeacon(self, device) -> bool:
        """Check if device is an iBeacon"""
        # Check manufacturer data for Apple iBeacon format
        if device.metadata.get('manufacturer_data'):
            for manufacturer_id, data in device.metadata['manufacturer_data'].items():
                if manufacturer_id == 0x004C and len(data) >= 23:  # Apple ID
                    return data[0] == 0x02 and data[1] == 0x15  # iBeacon
        return False
    
    def _parse_ibeacon(self, device) -> Dict[str, Any]:
        """Parse iBeacon data from device"""
        for manufacturer_id, data in device.metadata['manufacturer_data'].items():
            if manufacturer_id == 0x004C:
                uuid = data[2:18].hex()
                major = int.from_bytes(data[18:20], 'big')
                minor = int.from_bytes(data[20:22], 'big')
                return {
                    'uuid': uuid,
                    'major': major,
                    'minor': minor
                }
        return {}
    
    async def cleanup(self):
        """Cleanup scanner resources"""
        pass