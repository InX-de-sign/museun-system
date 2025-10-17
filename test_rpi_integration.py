# test_rpi_integration.py - Test complete RPi integration
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tts_endpoint(server_url: str):
    """Test TTS WebSocket endpoint"""
    logger.info("Testing TTS endpoint...")
    
    uri = f"{server_url}/ws/tts"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Register
            await websocket.send(json.dumps({
                "type": "register",
                "client_id": "test_client"
            }))
            
            # Wait for confirmation
            response = await websocket.recv()
            logger.info(f"Registration response: {response}")
            
            # Send test query
            await websocket.send(json.dumps({
                "type": "text_query",
                "text": "Tell me about Van Gogh"
            }))
            
            # Receive streaming responses
            sentence_count = 0
            while True:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=30.0
                )
                data = json.loads(response)
                
                if data.get("type") == "stream_chunk":
                    sentence_count += 1
                    logger.info(f"Sentence {sentence_count}: {data.get('text')}")
                    
                elif data.get("type") == "stream_complete":
                    logger.info(f"✅ Received complete response: {sentence_count} sentences")
                    break
                    
        logger.info("TTS endpoint test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"TTS endpoint test FAILED: {e}")
        return False

async def test_health_endpoint(server_url: str):
    """Test health endpoint"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url.replace('ws://', 'http://')}/health") as response:
                data = await response.json()
                logger.info(f"Health check: {data}")
                
                if data.get("status") == "healthy":
                    logger.info("✅ Health check PASSED")
                    return True
                else:
                    logger.error("❌ Health check FAILED")
                    return False
                    
    except Exception as e:
        logger.error(f"Health check FAILED: {e}")
        return False

async def run_all_tests(server_url: str):
    """Run all integration tests"""
    logger.info("="*60)
    logger.info("Starting RPi Integration Tests")
    logger.info("="*60)
    
    results = []
    
    # Test 1: Health endpoint
    logger.info("\nTest 1: Health Endpoint")
    results.append(await test_health_endpoint(server_url))
    
    # Test 2: TTS endpoint
    logger.info("\nTest 2: TTS WebSocket Endpoint")
    results.append(await test_tts_endpoint(server_url))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    passed = sum(results)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED!")
    else:
        logger.error("❌ SOME TESTS FAILED")
    
    return passed == total

if __name__ == "__main__":
    # Change this to your server URL
    SERVER_URL = "ws://localhost:8000"
    
    asyncio.run(run_all_tests(SERVER_URL))