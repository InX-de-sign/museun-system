"""
Service connector for communication with cloud services
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ServiceConnector:
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config['url']
        self.session = None
        self.connected = False
        
    async def initialize(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
        self.session = aiohttp.ClientSession(timeout=timeout)
        await self.check_connection()
    
    async def check_connection(self) -> bool:
        """Check connection to API gateway"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                self.connected = response.status == 200
                return self.connected
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            self.connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to cloud"""
        return self.connected
    
    async def send_beacon_data(self, readings: List[Dict[str, Any]]):
        """Send beacon readings to localization service"""
        try:
            endpoint = f"{self.base_url}/localization/process_beacons"
            async with self.session.post(endpoint, json=readings) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to send beacon data: {response.status}")
        except Exception as e:
            logger.error(f"Error sending beacon data: {e}")
            self.connected = False
    
    async def send_audio(self, audio_data: bytes) -> Optional[bytes]:
        """Send audio to chatbot service"""
        try:
            endpoint = f"{self.base_url}/chatbot/process_audio"
            
            data = aiohttp.FormData()
            data.add_field('audio', audio_data, 
                          filename='audio.wav',
                          content_type='audio/wav')
            
            async with self.session.post(endpoint, data=data) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to send audio: {response.status}")
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            self.connected = False
        return None
    
    async def analyze_image(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Send image to CV service for analysis"""
        try:
            endpoint = f"{self.base_url}/cv/analyze"
            
            data = aiohttp.FormData()
            data.add_field('file', image_data,
                          filename='image.jpg',
                          content_type='image/jpeg')
            
            async with self.session.post(endpoint, data=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to analyze image: {response.status}")
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            self.connected = False
        return None
    
    async def sync_data(self, buffered_data: List[Dict[str, Any]]) -> bool:
        """Sync buffered data to cloud"""
        try:
            endpoint = f"{self.base_url}/sync"
            
            for attempt in range(self.config['retry_count']):
                try:
                    async with self.session.post(endpoint, json=buffered_data) as response:
                        if response.status == 200:
                            return True
                        else:
                            logger.warning(f"Sync failed with status: {response.status}")
                except Exception as e:
                    logger.warning(f"Sync attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(self.config['retry_delay'])
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing data: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()