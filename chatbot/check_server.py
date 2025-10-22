#!/usr/bin/env python3
# check_server.py - Verify server configuration
import os
import sys

print("="*60)
print("🔍 SERVER CONFIGURATION CHECK")
print("="*60)

# 1. Check OpenAI API Key
print("\n1️⃣ OpenAI API Key:")
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"   ✅ Set (starts with: {api_key[:10]}...)")
else:
    print("   ❌ NOT SET!")
    print("   Export it: export OPENAI_API_KEY='your-key-here'")

# 2. Test OpenAI Connection
print("\n2️⃣ Testing OpenAI Connection:")
try:
    from openai import AsyncOpenAI
    import asyncio
    
    async def test_openai():
        try:
            client = AsyncOpenAI(api_key=api_key)
            
            # Test Whisper API with a tiny audio file
            print("   Testing Whisper API...")
            
            # Create a minimal valid WAV file (1 second of silence)
            import wave
            import io
            
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)  # 16kHz
                # 1 second of silence
                silence = b'\x00' * (16000 * 2)
                wf.writeframes(silence)
            
            wav_buffer.seek(0)
            wav_buffer.name = "test.wav"
            
            # Try Whisper API
            result = await client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_buffer,
                language="en"
            )
            
            print(f"   ✅ Whisper API working!")
            print(f"   Result: '{result.text}' (empty is OK for silence)")
            return True
            
        except Exception as e:
            print(f"   ❌ OpenAI Error: {e}")
            return False
    
    result = asyncio.run(test_openai())
    
except ImportError:
    print("   ❌ OpenAI library not installed")
    print("   Install: pip install openai")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Check required files
print("\n3️⃣ Required Files:")
files = [
    "api.py",
    "audio_receiver.py",
    "optimized_voice.py",
    "main.py"
]

for file in files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
    else:
        print(f"   ⚠️ {file} (not found)")

# 4. Check dependencies
print("\n4️⃣ Python Dependencies:")
deps = [
    ("fastapi", "FastAPI"),
    ("websockets", "WebSockets"),
    ("openai", "OpenAI"),
    ("uvicorn", "Uvicorn")
]

for module, name in deps:
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} not installed")

print("\n" + "="*60)
print("🏁 DIAGNOSTIC COMPLETE")
print("="*60)

if not api_key:
    print("\n⚠️ CRITICAL: Set OPENAI_API_KEY before running server!")
    print("   export OPENAI_API_KEY='sk-your-key-here'")
else:
    print("\n✅ Server should be ready to run!")
    print("   Start with: python api.py")