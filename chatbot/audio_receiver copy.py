# audio_receiver.py - Server-side audio receiver (UPDATED)
import asyncio
import json
import base64
import logging
from typing import Optional, Dict
from fastapi import WebSocket
from collections import deque
from optimized_voice import OptimizedVoiceComponent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioReceiver:
    """Receives and processes audio from Raspberry Pi clients"""
    
    def __init__(self, voice_component: OptimizedVoiceComponent):
        self.voice_component = voice_component
        self.audio_queues: Dict[str, deque] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.client_settings: Dict[str, dict] = {}
        
    async def handle_client(self, websocket: WebSocket, client_id: str):
        """Handle audio from a single RPi client"""
        logger.info(f"Audio receiver started for client: {client_id}")
        
        # Create queue for this client
        self.audio_queues[client_id] = deque(maxlen=100)  # Increased for streaming
        
        # Start processing task
        self.processing_tasks[client_id] = asyncio.create_task(
            self._process_audio_queue(client_id, websocket)
        )
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "register":
                    # Store client settings
                    self.client_settings[client_id] = data.get("audio_settings", {})
                    logger.info(f"Client registered: {client_id} with settings: {self.client_settings[client_id]}")
                    
                    await websocket.send_json({
                        "type": "registered",
                        "message": "Client registered successfully"
                    })
                
                elif data.get("type") == "audio_chunk":
                    audio_base64 = data.get("audio")
                    chunk_id = data.get("chunk_id", 0)
                    
                    # Decode audio
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    if chunk_id % 10 == 0:  # Log every 10 chunks
                        logger.info(f"Received chunk {chunk_id}: {len(audio_bytes)} bytes")
                    
                    # Add to queue
                    self.audio_queues[client_id].append({
                        "audio": audio_bytes,
                        "chunk_id": chunk_id,
                        "format": data.get("format", "audio/wav"),
                        "timestamp": data.get("timestamp")
                    })
                    
                elif data.get("type") == "audio_complete":
                    logger.info(f"Audio complete for {client_id}, total chunks: {data.get('total_chunks')}")
                    # Signal end of utterance
                    self.audio_queues[client_id].append({"type": "complete"})
                    
        except Exception as e:
            logger.error(f"Audio receiver error for {client_id}: {e}")
        finally:
            # Cleanup
            if client_id in self.processing_tasks:
                self.processing_tasks[client_id].cancel()
                try:
                    await self.processing_tasks[client_id]
                except asyncio.CancelledError:
                    pass
            if client_id in self.audio_queues:
                del self.audio_queues[client_id]
            if client_id in self.client_settings:
                del self.client_settings[client_id]
    
    async def _process_audio_queue(self, client_id: str, websocket: WebSocket):
        """Process queued audio chunks for STT"""
        accumulated_audio = bytearray()
        chunk_count = 0
        
        while True:
            try:
                # Wait for audio in queue
                if not self.audio_queues[client_id]:
                    await asyncio.sleep(0.05)
                    continue
                
                chunk_data = self.audio_queues[client_id].popleft()
                
                # Check for completion signal
                if chunk_data.get("type") == "complete":
                    if accumulated_audio and len(accumulated_audio) > 1000:
                        logger.info(f"Processing final audio: {len(accumulated_audio)} bytes")
                        
                        # Process accumulated audio
                        text = await self._process_accumulated_audio(
                            bytes(accumulated_audio),
                            chunk_data.get("format", "audio/wav")
                        )
                        
                        if text:
                            # Send recognized text back to client
                            await websocket.send_json({
                                "type": "stt_result",
                                "text": text,
                                "client_id": client_id,
                                "chunk_count": chunk_count
                            })
                            logger.info(f"✅ STT Result: '{text}'")
                        else:
                            await websocket.send_json({
                                "type": "stt_result",
                                "text": "",
                                "client_id": client_id,
                                "error": "No speech detected"
                            })
                        
                        # Reset accumulator
                        accumulated_audio = bytearray()
                        chunk_count = 0
                    continue
                
                # Accumulate audio chunks
                audio_bytes = chunk_data.get("audio")
                if audio_bytes:
                    accumulated_audio.extend(audio_bytes)
                    chunk_count += 1
                    
                    # Process in batches (every ~2 seconds of audio)
                    # 44100 Hz * 2 bytes (16-bit) * 2 seconds = ~176KB
                    if len(accumulated_audio) >= 176000:
                        logger.info(f"Processing batch: {len(accumulated_audio)} bytes from {chunk_count} chunks")
                        
                        text = await self._process_accumulated_audio(
                            bytes(accumulated_audio),
                            chunk_data.get("format", "audio/wav")
                        )
                        
                        if text:
                            await websocket.send_json({
                                "type": "stt_partial",
                                "text": text,
                                "client_id": client_id,
                                "is_partial": True
                            })
                            logger.info(f"Partial STT: '{text}'")
                        
                        # Keep last 0.5s for context
                        overlap_size = 44100  # ~0.5 seconds at 44.1kHz
                        accumulated_audio = accumulated_audio[-overlap_size:]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(0.5)
    
    async def _process_accumulated_audio(self, audio_bytes: bytes, format: str) -> Optional[str]:
        """Run STT on accumulated audio"""
        if len(audio_bytes) < 1000:
            logger.debug("Audio too short for STT")
            return None
        
        try:
            logger.info(f"Running STT on {len(audio_bytes)} bytes...")
            
            # Use your existing voice component for STT
            text = await asyncio.wait_for(
                self.voice_component.process_audio_to_text_async(
                    audio_bytes,
                    format
                ),
                timeout=15.0
            )
            
            return text.strip() if text else None
            
        except asyncio.TimeoutError:
            logger.error("STT timeout")
            return None
        except Exception as e:
            logger.error(f"STT processing error: {e}")
            return None