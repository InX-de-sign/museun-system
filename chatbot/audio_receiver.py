# audio_receiver.py - Complete workflow: STT → OpenAI → TTS
import asyncio
import json
import base64
import logging
import wave
import io
from typing import Optional, Dict
from fastapi import WebSocket
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioReceiver:
    """Receives and processes audio from Raspberry Pi clients"""
    
    def __init__(self, voice_component, assistant=None, tts_connections=None, stream_func=None):
        self.voice_component = voice_component
        self.assistant = assistant  # NEW: OpenAI assistant
        self.tts_connections = tts_connections  # NEW: TTS WebSocket connections
        self.stream_func = stream_func  # NEW: Function to stream response
        
        self.audio_queues: Dict[str, deque] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.client_settings: Dict[str, dict] = {}
        
        if not voice_component:
            logger.error("❌ Voice component required!")
        else:
            logger.info("✅ Audio receiver initialized")

    # Add this method to your AudioReceiver class in audio_receiver.py
    # Add it right after the __init__ method

    async def handle_client_with_id(self, websocket: WebSocket, client_id: str, first_message: dict):
        """Handle audio from RPi client with pre-determined client_id"""
        logger.info(f"🎤 Audio receiver started for client: {client_id}")
        
        self.audio_queues[client_id] = deque(maxlen=300)
        self.processing_tasks[client_id] = asyncio.create_task(
            self._process_audio_queue(client_id, websocket)
        )
        
        # Process the first message (registration)
        if first_message.get("type") == "register":
            self.client_settings[client_id] = first_message.get("audio_settings", {})
            logger.info(f"✅ Registered: {client_id}")
            
            await websocket.send_json({
                "type": "registered",
                "message": "Registered"
            })
        
        try:
            # Continue handling messages
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "audio_chunk":
                    audio_base64 = data.get("audio")
                    audio_bytes = base64.b64decode(audio_base64)
                    chunk_id = data.get("chunk_id", 0)
                    
                    if chunk_id % 50 == 0 and chunk_id > 0:
                        logger.info(f"📥 Chunk {chunk_id}")
                    
                    self.audio_queues[client_id].append(audio_bytes)
                    
                elif data.get("type") == "audio_complete":
                    total_chunks = data.get('total_chunks', 0)
                    logger.info(f"🎤 Complete: {total_chunks} chunks")
                    
                    self.audio_queues[client_id].append("COMPLETE")
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
        finally:
            if client_id in self.processing_tasks:
                self.processing_tasks[client_id].cancel()
            if client_id in self.audio_queues:
                del self.audio_queues[client_id]
            logger.info(f"🔌 Disconnected: {client_id}")

    async def handle_client(self, websocket: WebSocket, client_id: str):
        """Handle audio from RPi client"""
        logger.info(f"🎤 Audio client connected: {client_id}")
        
        self.audio_queues[client_id] = deque(maxlen=300)
        self.processing_tasks[client_id] = asyncio.create_task(
            self._process_audio_queue(client_id, websocket)
        )
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "register":
                    self.client_settings[client_id] = data.get("audio_settings", {})
                    logger.info(f"✅ Registered: {client_id}")
                    
                    await websocket.send_json({
                        "type": "registered",
                        "message": "Registered"
                    })
                
                elif data.get("type") == "audio_chunk":
                    audio_base64 = data.get("audio")
                    audio_bytes = base64.b64decode(audio_base64)
                    chunk_id = data.get("chunk_id", 0)
                    
                    if chunk_id % 50 == 0 and chunk_id > 0:
                        logger.info(f"📥 Chunk {chunk_id}")
                    
                    self.audio_queues[client_id].append(audio_bytes)
                    
                elif data.get("type") == "audio_complete":
                    total_chunks = data.get('total_chunks', 0)
                    logger.info(f"🎤 Complete: {total_chunks} chunks")
                    
                    self.audio_queues[client_id].append("COMPLETE")
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
        finally:
            if client_id in self.processing_tasks:
                self.processing_tasks[client_id].cancel()
            if client_id in self.audio_queues:
                del self.audio_queues[client_id]
            logger.info(f"🔌 Disconnected: {client_id}")
    
    async def _process_audio_queue(self, client_id: str, websocket: WebSocket):
        """Process audio chunks → STT → OpenAI → TTS"""
        audio_chunks = []
        
        while True:
            try:
                if not self.audio_queues[client_id]:
                    await asyncio.sleep(0.05)
                    continue
                
                item = self.audio_queues[client_id].popleft()
                
                if item == "COMPLETE":
                    if len(audio_chunks) > 10:
                        logger.info(f"🎯 Processing {len(audio_chunks)} chunks")
                        
                        await websocket.send_json({
                            "type": "stt_processing",
                            "message": "Processing speech..."
                        })
                        
                        # Combine chunks
                        combined_wav = self._combine_to_proper_wav(audio_chunks, client_id)
                        
                        if combined_wav:
                            logger.info(f"Combined WAV: {len(combined_wav)} bytes")
                            
                            # Save debug file
                            try:
                                import os
                                os.makedirs("debug_audio", exist_ok=True)
                                debug_file = f"debug_audio/server_{client_id}.wav"
                                with open(debug_file, 'wb') as f:
                                    f.write(combined_wav)
                                logger.info(f"💾 Saved debug file: {debug_file}")
                            except:
                                pass
                            
                            # STT
                            text = await self._google_stt(combined_wav)
                            
                            if text and text.strip():
                                logger.info(f"✅ STT: '{text}'")
                                
                                # Send STT result
                                await websocket.send_json({
                                    "type": "stt_result",
                                    "text": text,
                                    "client_id": client_id
                                })
                                
                                # COMPLETE WORKFLOW: Get OpenAI response and stream to TTS
                                await self._process_with_openai(text, client_id, websocket)
                                
                            else:
                                logger.warning("⚠️ Empty STT")
                                await websocket.send_json({
                                    "type": "stt_result",
                                    "text": "",
                                    "error": "No speech detected"
                                })
                        else:
                            logger.error("❌ Failed to combine chunks")
                        
                        audio_chunks = []
                    continue
                
                audio_chunks.append(item)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Processing error: {e}", exc_info=True)
    
    async def _process_with_openai(self, text: str, client_id: str, audio_ws: WebSocket):
        """Process text with OpenAI and stream response to TTS"""
        if not self.assistant or not self.tts_connections or not self.stream_func:
            logger.warning("⚠️ OpenAI components not configured")
            return
        
        # Get TTS WebSocket
        tts_ws = self.tts_connections.get(client_id)
        if not tts_ws:
            logger.warning(f"⚠️ No TTS connection for {client_id}")
            return
        
        try:
            logger.info(f"🤖 Processing with OpenAI: '{text}'")
            
            # Notify processing
            await audio_ws.send_json({
                "type": "openai_processing",
                "message": "Getting AI response..."
            })
            
            # Get response from assistant
            response = await self.assistant.process_message(text, client_id)
            
            logger.info(f"✅ Got OpenAI response: {response[:50]}...")
            
            # Stream to TTS client
            await self.stream_func(response, tts_ws, client_id)
            
            logger.info("✅ Complete workflow finished")
            
        except Exception as e:
            logger.error(f"❌ OpenAI processing error: {e}", exc_info=True)
            await audio_ws.send_json({
                "type": "error",
                "message": f"AI processing failed: {str(e)}"
            })
    
    def _combine_to_proper_wav(self, chunks: list, client_id: str) -> Optional[bytes]:
        """Combine WAV chunks properly"""
        try:
            settings = self.client_settings.get(client_id, {})
            sample_rate = settings.get("sample_rate", 44100)
            channels = settings.get("channels", 1)
            
            logger.info(f"Combining {len(chunks)} chunks (rate={sample_rate}, channels={channels})")
            
            all_audio_data = []
            
            for i, chunk in enumerate(chunks):
                try:
                    chunk_io = io.BytesIO(chunk)
                    with wave.open(chunk_io, 'rb') as wf:
                        audio_frames = wf.readframes(wf.getnframes())
                        all_audio_data.append(audio_frames)
                except Exception as e:
                    logger.warning(f"Chunk {i} error: {e}")
                    continue
            
            if not all_audio_data:
                return None
            
            combined_audio_data = b''.join(all_audio_data)
            logger.info(f"Combined {len(all_audio_data)} chunks → {len(combined_audio_data)} bytes raw audio")
            
            output_buffer = io.BytesIO()
            with wave.open(output_buffer, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(combined_audio_data)
            
            result = output_buffer.getvalue()
            logger.info(f"✅ Created proper WAV: {len(result)} bytes total")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Combining error: {e}", exc_info=True)
            return None
    
    async def _google_stt(self, audio_bytes: bytes) -> Optional[str]:
        """Google Speech Recognition"""
        if not self.voice_component:
            return None
        
        if len(audio_bytes) < 10000:
            logger.warning(f"⚠️ Audio too short: {len(audio_bytes)} bytes")
            return None
        
        try:
            logger.info(f"🎙️ Running STT on {len(audio_bytes)} bytes...")
            
            text = await asyncio.wait_for(
                self.voice_component.process_audio_to_text_async(
                    audio_bytes,
                    "audio/wav"
                ),
                timeout=30.0
            )
            
            if text and text.strip():
                logger.info(f"✅ STT success: '{text}'")
                return text.strip()
            else:
                logger.warning("⚠️ STT returned empty")
                return None
            
        except asyncio.TimeoutError:
            logger.error("❌ STT timeout")
            return None
        except Exception as e:
            logger.error(f"❌ STT error: {e}", exc_info=True)
            return None