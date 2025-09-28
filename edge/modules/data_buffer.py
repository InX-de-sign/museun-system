"""
Data buffer module for offline storage and sync
"""
import asyncio
import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DataBuffer:
    def __init__(self, config: dict):
        self.config = config
        self.db_path = config['database_path']
        self.max_size = config['max_size'] * 1024 * 1024  # Convert to bytes
        
    async def initialize(self):
        """Initialize SQLite database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0
                )
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_synced ON buffer(synced)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON buffer(timestamp)
            ''')
            await db.commit()
    
    async def add_beacon_data(self, readings: List[Dict[str, Any]]):
        """Add beacon readings to buffer"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO buffer (type, data) VALUES (?, ?)",
                ('beacon', json.dumps(readings))
            )
            await db.commit()
    
    async def add_audio_data(self, audio_data: bytes):
        """Add audio data to buffer"""
        # Store audio as base64 encoded string
        import base64
        encoded = base64.b64encode(audio_data).decode('utf-8')
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO buffer (type, data) VALUES (?, ?)",
                ('audio', encoded)
            )
            await db.commit()
    
    async def add_image_data(self, image_data: bytes):
        """Add image data to buffer"""
        import base64
        encoded = base64.b64encode(image_data).decode('utf-8')
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO buffer (type, data) VALUES (?, ?)",
                ('image', encoded)
            )
            await db.commit()
    
    async def get_pending_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unsynced data from buffer"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, type, data, timestamp FROM buffer WHERE synced = 0 ORDER BY timestamp LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'type': row[1],
                    'data': json.loads(row[2]) if row[1] == 'beacon' else row[2],
                    'timestamp': row[3]
                }
                for row in rows
            ]
    
    async def mark_synced(self, ids: List[int]):
        """Mark data as synced"""
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ','.join('?' * len(ids))
            await db.execute(
                f"UPDATE buffer SET synced = 1 WHERE id IN ({placeholders})",
                ids
            )
            await db.commit()
    
    async def clear_synced_data(self):
        """Remove old synced data"""
        retention_date = datetime.utcnow() - timedelta(days=self.config['retention_days'])
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM buffer WHERE synced = 1 AND timestamp < ?",
                (retention_date.isoformat(),)
            )
            await db.commit()
    
    async def cleanup(self):
        """Cleanup database connection"""
        await self.clear_synced_data()