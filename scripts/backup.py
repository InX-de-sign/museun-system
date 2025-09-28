#!/usr/bin/env python3
"""
Backup script for databases and important data
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path

def backup_postgres():
    """Backup PostgreSQL databases"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups") / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    databases = ['museum_db', 'chatbot_db', 'localization_db', 'analytics_db']
    
    for db in databases:
        backup_file = backup_dir / f"{db}.sql"
        cmd = [
            'docker-compose', 'exec', '-T', 'postgres',
            'pg_dump', '-U', 'museum_user', db
        ]
        
        with open(backup_file, 'w') as f:
            subprocess.run(cmd, stdout=f)
        
        print(f"Backed up {db} to {backup_file}")

def backup_redis():
    """Backup Redis data"""
    cmd = ['docker-compose', 'exec', 'redis', 'redis-cli', 'BGSAVE']
    subprocess.run(cmd)
    print("Redis backup initiated")

if __name__ == "__main__":
    backup_postgres()
    backup_redis()
    print("Backup complete!")