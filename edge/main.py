#!/usr/bin/env python3
"""
Simplified edge device for beacon and camera only
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime

import yaml
from modules.beacon_scanner import BeaconScanner
from modules.camera_handler import CameraHandler
from modules.data_buffer import DataBuffer
from modules.service_connector import ServiceConnector

logger = logging.getLogger(__name__)

class EdgeDevice:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self.load_config(config_path)
        self.running = False
        
        # Initialize only needed modules
        self.beacon_scanner = BeaconScanner(self.config['beacon'])
        self.camera_handler = CameraHandler(self.config['camera'])
        self.data_buffer = DataBuffer(self.config['buffer'])
        self.service_connector = ServiceConnector(self.config['api_gateway'])
        
    async def process_beacon_data(self):
        """
        Main beacon logic:
        1. Scan for iBeacons every second
        2. Send RSSI values to cloud
        3. Cloud calculates position
        4. Position used by chatbot for context
        """
        while self.running:
            try:
                # Get beacon readings
                readings = await self.beacon_scanner.scan()
                
                if readings:
                    # Send to localization service for position calculation
                    location = await self.service_connector.send_beacon_data(
                        user_id=self.config['device']['user_id'],
                        readings=readings
                    )
                    
                    if location:
                        logger.info(f"User location: Zone={location['zone']}, "
                                  f"Confidence={location['confidence']}")
                    
                    # Store locally if offline
                    if not self.service_connector.is_connected():
                        await self.data_buffer.add_beacon_data(readings)
                
                await asyncio.sleep(self.config['beacon']['scan_interval'])
                
            except Exception as e:
                logger.error(f"Beacon processing error: {e}")
    
    async def process_camera(self):
        """
        Camera logic:
        1. Triggered by button or proximity
        2. Capture image
        3. Send to CV service for analysis
        4. Results enhance chatbot context
        """
        while self.running:
            try:
                # Check for trigger (button press)
                if self.camera_handler.should_capture():
                    image = await self.camera_handler.capture_image()
                    
                    if image and self.service_connector.is_connected():
                        # Send to CV service
                        analysis = await self.service_connector.analyze_image(image)
                        
                        if analysis:
                            # Update chatbot context with what child is looking at
                            await self.service_connector.update_context({
                                "user_id": self.config['device']['user_id'],
                                "viewing": analysis['detected_objects'],
                                "paintings": analysis.get('paintings', [])
                            })
                    else:
                        # Store for later if offline
                        await self.data_buffer.add_image_data(image)
                
                await asyncio.sleep(0.1)  # Quick response for button
                
            except Exception as e:
                logger.error(f"Camera processing error: {e}")
    
    async def sync_buffered_data(self):
        """Sync offline data when connection restored"""
        while self.running:
            try:
                if self.service_connector.is_connected():
                    await self.data_buffer.sync_to_cloud(self.service_connector)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Sync error: {e}")

    async def start(self):
        """Start edge device services"""
        self.running = True
        logger.info(f"Starting Edge Device: {self.config['device']['id']}")
        
        # Initialize components
        await self.data_buffer.initialize()
        await self.service_connector.initialize()
        
        # Create concurrent tasks
        tasks = [
            asyncio.create_task(self.process_beacon_data()),
            asyncio.create_task(self.process_camera()),
            asyncio.create_task(self.sync_buffered_data()),
        ]
        
        await asyncio.gather(*tasks)