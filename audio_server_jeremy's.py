from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import wave
import numpy as np
from datetime import datetime
import os
import json
from typing import Optional

app = FastAPI(title="Audio Streaming Server")

# 允許跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 創建音頻儲存目錄
AUDIO_STORAGE = "received_audio"
os.makedirs(AUDIO_STORAGE, exist_ok=True)

@app.post("/upload_audio")
async def upload_audio(
    audio_file: UploadFile = File(...),
    timestamp: float = Form(...),
    sample_rate: int = Form(44100),
    channels: int = Form(1),
    duration: Optional[float] = Form(None)
):
    """接收上傳的音頻文件"""
    try:
        # 驗證文件類型
        if not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Invalid audio file")
        
        # 讀取音頻數據
        contents = await audio_file.read()
        
        # 生成文件名
        filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        filepath = os.path.join(AUDIO_STORAGE, filename)
        
        # 保存音頻文件
        with open(filepath, 'wb') as f:
            f.write(contents)
        
        # 讀取音頻信息
        with wave.open(filepath, 'rb') as wf:
            frames = wf.getnframes()
            actual_rate = wf.getframerate()
            actual_channels = wf.getnchannels()
        
        # 處理音頻數據 (這裡可以添加您的音頻處理邏輯)
        audio_data = await process_audio_data(contents)
        
        # 記錄接收信息
        log_entry = {
            "filename": filename,
            "timestamp": timestamp,
            "received_time": datetime.now().isoformat(),
            "sample_rate": actual_rate,
            "channels": actual_channels,
            "frames": frames,
            "duration": frames / actual_rate if actual_rate > 0 else 0
        }
        
        # 保存日誌
        log_filename = f"audio_log_{datetime.now().strftime('%Y%m%d')}.json"
        log_path = os.path.join(AUDIO_STORAGE, log_filename)
        
        logs = []
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        
        with open(log_path, 'w') as f:
            json.dump(logs, f, indent=2)
        
        return {
            "status": "success",
            "message": "Audio received successfully",
            "filename": filename,
            "file_size": len(contents),
            "duration": log_entry["duration"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

async def process_audio_data(audio_bytes: bytes) -> dict:
    """處理音頻數據的示例函數"""
    try:
        # 將音頻字節轉換為 numpy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # 計算基本統計信息
        audio_info = {
            "max_amplitude": float(np.max(audio_array)),
            "min_amplitude": float(np.min(audio_array)),
            "mean_amplitude": float(np.mean(audio_array)),
            "rms": float(np.sqrt(np.mean(audio_array**2))),
            "length": len(audio_array)
        }
        
        print(f"Processed audio: {audio_info}")
        return audio_info
        
    except Exception as e:
        print(f"Audio processing error: {e}")
        return {}

@app.get("/")
async def root():
    return {"message": "Audio Streaming Server is running"}

@app.get("/audio_files")
async def list_audio_files():
    """列出所有接收到的音頻文件"""
    files = []
    for filename in os.listdir(AUDIO_STORAGE):
        if filename.endswith('.wav'):
            filepath = os.path.join(AUDIO_STORAGE, filename)
            stats = os.stat(filepath)
            files.append({
                "filename": filename,
                "size": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
            })
    return {"files": files}

if __name__ == "__main__":
    uvicorn.run(
        "audio_server:app",
        host="0.0.0.0",  # 允許外部訪問
        port=8000,
        reload=True
    )