#!/usr/bin/env python3
"""
Setup script for Windows - Creates database and adds OpenFish
Fixes common Windows/PostgreSQL connection issues
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import Json
import os
import sys

# Kid-friendly description
KID_FRIENDLY_DESCRIPTION = """Meet OpenFish - a super cool robot fish that swims just like a real tuna! Scientists and engineers created this amazing fish using special soft materials that bend and move. It can zoom through the water at 0.85 meters per second - that's faster than you can walk! The best part? OpenFish is like a LEGO set that anyone can build and make even better. Students at HKUST are working on making it swim even faster by improving its tail movement and body shape."""

CURATOR_WORDS = """OpenFish is now a project worked on by different students in Integrative Systems and Design, HKUST at ISDN2400 Physical Prototyping too. It provides a challenge for students to improve on its mechanism and fluid dynamics design, to improve on its speed."""

def get_connection_params():
    """Get PostgreSQL connection parameters for Windows/localhost"""
    return {
        'host': 'localhost',  # Use localhost when running from Windows host
        'port': '5432',
        'user': 'museum_user',
        'password': 'museum_pass',  # Default password, change if different
        'dbname': 'postgres'  # Connect to default postgres db first
    }

def create_database_if_not_exists():
    """Create chatbot_db if it doesn't exist"""
    print("\n" + "="*70)
    print("Step 1: Creating database if needed...")
    print("="*70)
    
    conn_params = get_connection_params()
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if chatbot_db exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='chatbot_db'")
        exists = cursor.fetchone()
        
        if exists:
            print("✓ Database 'chatbot_db' already exists")
        else:
            print("Creating database 'chatbot_db'...")
            cursor.execute("CREATE DATABASE chatbot_db")
            print("✓ Database 'chatbot_db' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check PostgreSQL is running: docker-compose ps")
        print("2. Check port 5432 is accessible: netstat -an | findstr 5432")
        print("3. Verify password is 'museum_pass' (or update script)")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def create_table_if_not_exists():
    """Create museum_objects table if it doesn't exist"""
    print("\n" + "="*70)
    print("Step 2: Creating table if needed...")
    print("="*70)
    
    conn_params = get_connection_params()
    conn_params['dbname'] = 'chatbot_db'
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS museum_objects (
                id SERIAL PRIMARY KEY,
                object_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(200),
                description TEXT,
                location VARCHAR(100),
                category VARCHAR(50),
                metadata JSONB
            )
        """)
        
        conn.commit()
        print("✓ Table 'museum_objects' ready")
        
        # Check if any objects exist
        cursor.execute("SELECT COUNT(*) FROM museum_objects")
        count = cursor.fetchone()[0]
        print(f"  Current objects in table: {count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        return False

def add_openfish():
    """Add OpenFish to the database"""
    print("\n" + "="*70)
    print("Step 3: Adding OpenFish...")
    print("="*70)
    
    conn_params = get_connection_params()
    conn_params['dbname'] = 'chatbot_db'
    
    # Prepare metadata
    metadata = {
        'artist': 'Sander C. van den Berg, Rob B.N. Scharff, Zoltán Rusák, Jun Wu',
        'date_painted': '2022',
        'year': 2022,
        'size': '40 × 15 cm',
        'dimensions': {
            'length_cm': 40,
            'width_cm': 15
        },
        'media': 'Sculpture',
        'type': 'Soft Robotic Fish',
        'curator_words': CURATOR_WORDS,
        'keywords': ['robot', 'fish', 'soft robotics', 'engineering', 'HKUST', 'OpenFish'],
        'educational_level': 'ages 7-10',
        'speed': '0.85 m/s'
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Check if OpenFish already exists
        cursor.execute("SELECT id, name FROM museum_objects WHERE object_id = %s", ('openfish_001',))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  OpenFish already exists (ID: {existing[0]})")
            response = input("Do you want to update it? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                cursor.execute("""
                    UPDATE museum_objects 
                    SET name = %s, description = %s, location = %s, category = %s, metadata = %s
                    WHERE object_id = %s
                    RETURNING id
                """, ('OpenFish', KID_FRIENDLY_DESCRIPTION, '2_a', 'sculpture', Json(metadata), 'openfish_001'))
                obj_id = cursor.fetchone()[0]
                conn.commit()
                print(f"✓ OpenFish updated (ID: {obj_id})")
            else:
                print("Skipped.")
                cursor.close()
                conn.close()
                return True
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO museum_objects 
                (object_id, name, description, location, category, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, ('openfish_001', 'OpenFish', KID_FRIENDLY_DESCRIPTION, '2_a', 'sculpture', Json(metadata)))
            
            obj_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✓ OpenFish added successfully (ID: {obj_id})")
        
        # Show total count
        cursor.execute("SELECT COUNT(*) FROM museum_objects")
        total = cursor.fetchone()[0]
        print(f"✓ Total objects in database: {total}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error adding OpenFish: {e}")
        import traceback
        traceback.print_exc()
        return False

def view_all_objects():
    """Display all objects in the database"""
    print("\n" + "="*70)
    print("Museum Objects in Database")
    print("="*70)
    
    conn_params = get_connection_params()
    conn_params['dbname'] = 'chatbot_db'
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, object_id, name, category, location,
                   metadata->>'artist' as artist
            FROM museum_objects 
            ORDER BY id
        """)
        
        objects = cursor.fetchall()
        
        if objects:
            print(f"\n{'ID':<5} {'Object ID':<20} {'Name':<35} {'Category':<12} {'Location':<10}")
            print("-" * 90)
            for obj in objects:
                obj_id, object_id, name, category, location, artist = obj
                print(f"{obj_id:<5} {object_id:<20} {name:<35} {category:<12} {location:<10}")
            print(f"\nTotal: {len(objects)} objects")
        else:
            print("No objects found.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("="*70)
    print("PostgreSQL Setup for Windows - Add OpenFish")
    print("="*70)
    print("\nThis script will:")
    print("1. Create chatbot_db database if needed")
    print("2. Create museum_objects table if needed")
    print("3. Add OpenFish artifact")
    print("\nConnection: localhost:5432 (from Windows host)")
    
    input("\nPress Enter to continue...")
    
    # Step 1: Create database
    if not create_database_if_not_exists():
        print("\n✗ Failed to create/connect to database")
        print("\nPlease check:")
        print("1. PostgreSQL container is running: docker-compose ps")
        print("2. Port 5432 is accessible")
        print("3. Password is correct (default: museum_pass)")
        sys.exit(1)
    
    # Step 2: Create table
    if not create_table_if_not_exists():
        print("\n✗ Failed to create table")
        sys.exit(1)
    
    # Step 3: Add OpenFish
    if not add_openfish():
        print("\n✗ Failed to add OpenFish")
        sys.exit(1)
    
    # Show results
    view_all_objects()
    
    print("\n" + "="*70)
    print("✓ Setup complete!")
    print("="*70)
    print("\nNEXT STEPS:")
    print("1. Update enhanced_rag_openai.py:")
    print('   Add: "openfish": ["openfish", "open fish", "robot fish"]')
    print()
    print("2. Update main.py:")
    print('   Add: "openfish", "robot fish" to artwork_keywords')
    print('   Add artists: "van den berg", "scharff", "rusák"')
    print()
    print("3. Restart services: make restart")
    print("="*70)

if __name__ == "__main__":
    main()