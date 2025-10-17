# main_client.py - Complete workflow with extensive debugging
import asyncio
import logging
import json
from audio_client_ws import AudioStreamingClient
from tts_client import TTSClient

# Enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MuseumRPiClient:
    """Complete Raspberry Pi client with full conversational workflow"""
    
    def __init__(self, server_url: str, client_id: str = "rpi_museum"):
        self.server_url = server_url
        self.client_id = client_id
        
        logger.info(f"🔧 Initializing client with URL: {server_url}, ID: {client_id}")
        
        # Initialize audio client
        self.audio_client = AudioStreamingClient(
            f"{server_url}/ws/audio",
            client_id
        )
        
        # Initialize TTS client
        self.tts_client = TTSClient(
            f"{server_url}/ws/tts",
            client_id
        )
        
        self.is_running = False
        self.waiting_for_response = False
        self.stt_result = None
        self.response_started = False
        self.response_count = 0
        
    async def start(self):
        """Start both audio and TTS clients"""
        logger.info("="*60)
        logger.info("🚀 Starting Museum RPi Client...")
        logger.info("="*60)
        
        self.is_running = True
        
        # Connect audio client
        logger.info("📡 Connecting audio client...")
        if not await self.audio_client.connect():
            logger.error("❌ Failed to connect audio client")
            print("\n❌ ERROR: Could not connect to audio WebSocket")
            print(f"Check if server is running at: {self.server_url}")
            return False
        logger.info("✅ Audio client connected")
        
        # Start TTS client in background
        logger.info("📡 Starting TTS client...")
        tts_task = asyncio.create_task(self.tts_client.connect_and_listen())
        await asyncio.sleep(1)  # Give it time to connect
        logger.info("✅ TTS client started")
        
        # Start audio listening task with custom handler
        logger.info("👂 Starting audio listener...")
        audio_listen_task = asyncio.create_task(
            self._listen_for_audio_responses()
        )
        logger.info("✅ Audio listener started")
        
        print("\n" + "="*60)
        print("✅ Museum RPi Client started successfully!")
        print("="*60)
        print("Press Ctrl+C to stop")
        
        try:
            # Main interaction loop
            while self.is_running:
                print("\n" + "="*60)
                print("Museum AI Assistant - Raspberry Pi")
                print("="*60)
                print("1. 🎤 Voice Conversation (COMPLETE WORKFLOW)")
                print("2. Record 5 seconds")
                print("3. Record 10 seconds")
                print("4. Manual recording (press Enter to stop)")
                print("5. Send text query")
                print("6. Exit")
                print("="*60)
                
                choice = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Choose option: "
                )
                
                logger.info(f"User selected option: {choice}")
                
                if choice == "1":
                    # *** COMPLETE CONVERSATIONAL WORKFLOW ***
                    await self.complete_conversation_workflow()
                    
                elif choice == "2":
                    logger.info("Recording 5 seconds...")
                    await self.audio_client.record_for_duration(5.0)
                    print("⏳ Waiting for server response...")
                    await asyncio.sleep(3)
                    
                elif choice == "3":
                    logger.info("Recording 10 seconds...")
                    await self.audio_client.record_for_duration(10.0)
                    print("⏳ Waiting for server response...")
                    await asyncio.sleep(3)
                    
                elif choice == "4":
                    print("🎤 Recording... Press Enter to stop")
                    recording_task = asyncio.create_task(
                        self.audio_client.start_recording()
                    )
                    
                    await asyncio.get_event_loop().run_in_executor(None, input)
                    
                    await self.audio_client.stop_recording()
                    recording_task.cancel()
                    print("⏳ Waiting for server response...")
                    await asyncio.sleep(3)
                    
                elif choice == "5":
                    text = await asyncio.get_event_loop().run_in_executor(
                        None, input, "Enter your question: "
                    )
                    
                    logger.info(f"Sending text query: {text}")
                    if self.audio_client.websocket:
                        await self.audio_client.websocket.send(json.dumps({
                            "type": "text_query",
                            "text": text,
                            "client_id": self.client_id
                        }))
                        logger.info("✅ Text query sent")
                        print("⏳ Waiting for AI response...")
                        await asyncio.sleep(2)
                    else:
                        logger.error("❌ WebSocket not connected!")
                    
                elif choice == "6":
                    logger.info("Exiting...")
                    self.is_running = False
                    break
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            # Cleanup
            logger.info("🧹 Cleaning up...")
            self.audio_client.cleanup()
            self.tts_client.shutdown()
            
            tts_task.cancel()
            audio_listen_task.cancel()
            
            try:
                await tts_task
            except asyncio.CancelledError:
                pass
            try:
                await audio_listen_task
            except asyncio.CancelledError:
                pass

    async def complete_conversation_workflow(self):
        """
        🎯 COMPLETE WORKFLOW with extensive debugging
        """
        print("\n" + "🎤 " + "="*58)
        print("COMPLETE VOICE CONVERSATION WORKFLOW")
        print("="*60)
        
        logger.info("="*60)
        logger.info("🎯 Starting complete workflow")
        logger.info("="*60)
        
        self.waiting_for_response = True
        self.stt_result = None
        self.response_started = False
        self.response_count = 0
        
        try:
            # STEP 1: Record audio
            print("\n📍 STEP 1: Recording your voice...")
            print("🎤 Speak now! (Recording for 5 seconds)")
            print("-" * 60)
            logger.info("STEP 1: Starting audio recording...")
            
            await self.audio_client.record_for_duration(5.0)
            
            print("✅ Recording complete!")
            logger.info("✅ Recording finished, audio sent to server")
            
            # STEP 2: Wait for STT result from server
            print("\n📍 STEP 2: Converting speech to text...")
            print("⏳ Processing with OpenAI Whisper...")
            logger.info("STEP 2: Waiting for STT result...")
            
            # Wait for STT result (server will send it back)
            timeout = 20  # 20 second timeout
            start_time = asyncio.get_event_loop().time()
            check_count = 0
            
            while self.stt_result is None:
                await asyncio.sleep(0.5)
                check_count += 1
                
                if check_count % 4 == 0:  # Every 2 seconds
                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.debug(f"Still waiting for STT... ({elapsed:.1f}s elapsed)")
                
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.error("❌ TIMEOUT waiting for STT result")
                    print("\n❌ Timeout waiting for STT result")
                    print("Possible issues:")
                    print("  1. Server didn't receive audio_complete message")
                    print("  2. Server didn't process STT")
                    print("  3. Server didn't send back stt_result")
                    print("\nCheck server logs for errors!")
                    return
            
            print(f"✅ You said: '{self.stt_result}'")
            logger.info(f"✅ STT received: '{self.stt_result}'")
            
            # STEP 3: Server automatically sends to OpenAI
            print("\n📍 STEP 3: Getting AI response from OpenAI...")
            print("🤖 Processing your question...")
            logger.info("STEP 3: Waiting for OpenAI response...")
            
            # STEP 4: Wait for response to start streaming
            print("\n📍 STEP 4: Receiving and playing AI response...")
            print("🔊 Listening for response chunks...")
            print("-" * 60)
            logger.info("STEP 4: Waiting for streaming response...")
            
            # Wait for response to start
            response_timeout = 15
            start_time = asyncio.get_event_loop().time()
            
            while not self.response_started:
                await asyncio.sleep(0.5)
                
                if asyncio.get_event_loop().time() - start_time > response_timeout:
                    logger.error("❌ No response received from server")
                    print("\n❌ No AI response received")
                    print("Possible issues:")
                    print("  1. Server didn't send to OpenAI")
                    print("  2. OpenAI API error")
                    print("  3. Server not streaming back response")
                    print("\nCheck server logs!")
                    return
            
            # Wait for complete response (give extra time)
            logger.info("✅ Response started, waiting for completion...")
            await asyncio.sleep(25)  # Longer wait for full response
            
            print("-" * 60)
            print(f"✅ Conversation complete! (Received {self.response_count} chunks)")
            print("="*60)
            logger.info(f"✅ Workflow completed successfully ({self.response_count} response chunks)")
            
        except Exception as e:
            logger.error(f"❌ Workflow error: {e}", exc_info=True)
            print(f"\n❌ Error in workflow: {e}")
        finally:
            self.waiting_for_response = False
    
    async def _listen_for_audio_responses(self):
        """Listen for server responses with extensive debugging"""
        logger.info("👂 Audio listener thread started")
        
        try:
            message_count = 0
            while True:
                if not self.audio_client.websocket:
                    logger.warning("⚠️ WebSocket not available, waiting...")
                    await asyncio.sleep(1)
                    continue
                
                try:
                    logger.debug("Waiting for message from server...")
                    message = await self.audio_client.websocket.recv()
                    message_count += 1
                    
                    logger.debug(f"📨 Received message #{message_count}: {message[:200]}")
                    
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    logger.info(f"📨 Message type: {message_type}")
                    
                    if message_type == "registered":
                        logger.info("✅ Client registered with server")
                        
                    elif message_type == "stt_result":
                        # Speech-to-text result from server
                        text = data.get("text", "")
                        self.stt_result = text  # Store for workflow
                        logger.info(f"🎤 STT RESULT: '{text}'")
                        print(f"\n🎤 STT: {text}")
                        
                    elif message_type == "stt_processing":
                        logger.info("⏳ Server processing speech...")
                        print("⏳ Server processing your speech...")
                        
                    elif message_type == "openai_processing":
                        logger.info("🤖 Server getting OpenAI response...")
                        print("🤖 Querying OpenAI...")
                        
                    elif message_type == "stream_start":
                        logger.info("🔊 Response stream starting...")
                        self.response_started = True
                        print("🔊 AI responding...")
                        
                    elif message_type == "response_chunk":
                        # Server sending response chunks
                        text = data.get("text", "")
                        self.response_count += 1
                        self.response_started = True
                        logger.info(f"💬 AI Chunk #{self.response_count}: {text[:100]}")
                        print(f"💬 [{self.response_count}] {text}")
                        
                    elif message_type == "stream_chunk":
                        # Alternative message type for streaming
                        text = data.get("text", "")
                        self.response_count += 1
                        self.response_started = True
                        logger.info(f"💬 Stream Chunk #{self.response_count}: {text[:100]}")
                        print(f"💬 [{self.response_count}] {text}")
                        
                    elif message_type == "response_complete":
                        total = data.get("total_sentences", 0)
                        logger.info(f"✅ Response complete ({total} sentences)")
                        print(f"\n✅ Response complete ({total} parts)")
                        
                    elif message_type == "stream_complete":
                        total = data.get("total_sentences", 0)
                        logger.info(f"✅ Stream complete ({total} sentences)")
                        
                    elif message_type == "error":
                        error_msg = data.get("message", "Unknown error")
                        logger.error(f"❌ SERVER ERROR: {error_msg}")
                        print(f"\n❌ Server Error: {error_msg}")
                        
                    elif message_type == "status":
                        status_msg = data.get("message", "")
                        logger.info(f"📊 Status: {status_msg}")
                        print(f"📊 {status_msg}")
                        
                    else:
                        logger.warning(f"⚠️ Unknown message type: {message_type}")
                        logger.debug(f"Full message: {data}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"Raw message: {message}")
                    
        except Exception as e:
            logger.error(f"❌ Listen error: {e}", exc_info=True)


async def main():
    """Main entry point with debugging"""
    # CHANGE THIS to your server IP
    SERVER_URL = "ws://100.88.240.42:8000"
    CLIENT_ID = "rpi_museum_1"
    
    print("="*60)
    print("🔊 Testing espeak-ng...")
    print("="*60)
    
    # Quick espeak test
    try:
        import subprocess
        result = subprocess.run(
            ['espeak-ng', '-v', 'en-us', '-s', '160', 'System ready'],
            check=True,
            timeout=5,
            capture_output=True
        )
        print("✅ espeak-ng working!")
        logger.info("✅ espeak-ng test passed")
    except Exception as e:
        print(f"⚠️ espeak-ng test failed: {e}")
        logger.error(f"⚠️ espeak-ng test failed: {e}")
        print("TTS may not work properly")
    
    print("\n🚀 Starting Museum Client...")
    print(f"Server URL: {SERVER_URL}")
    print(f"Client ID: {CLIENT_ID}")
    logger.info(f"Connecting to: {SERVER_URL}")
    
    client = MuseumRPiClient(SERVER_URL, CLIENT_ID)
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())