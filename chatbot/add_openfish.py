#!/usr/bin/env python3
"""
Script to add OpenFish artifact to museum.db
This includes both the technical description and a kid-friendly version
"""

import sqlite3
import os

# Original technical description
TECHNICAL_DESCRIPTION = """We present OpenFish: an open source soft robotic fish which is optimized for speed and efficiency. The soft robotic fish uses a combination of an active and passive tail segment to accurately mimic the thunniform swimming mode. Through the implementation of a novel propulsion system that is capable of achieving higher oscillation frequencies with a more sinusoidal waveform, the open source soft robotic fish achieves a top speed of 0.85m/s. Hereby, it outperforms the previously reported fastest soft robotic fish by 27%. Besides the propulsion system, the optimization of the fish morphology played a crucial role in achieving this speed. In this work, a detailed description of the design, construction and customization of the soft robotic fish is presented. Hereby, we hope this open source design will accelerate future research and developments in soft robotic fish."""

# Kid-friendly description (ages 7-10)
KID_FRIENDLY_DESCRIPTION = """Meet OpenFish - a super cool robot fish that swims just like a real tuna! Scientists and engineers created this amazing fish using special soft materials that bend and move. It can zoom through the water at 0.85 meters per second - that's faster than you can walk! The best part? OpenFish is like a LEGO set that anyone can build and make even better. Students at HKUST are working on making it swim even faster by improving its tail movement and body shape."""

CURATOR_WORDS = """OpenFish is now a project worked on by different students in Integrative Systems and Design, HKUST at ISDN2400 Physical Prototyping too. It provides a challenge for students to improve on its mechanism and fluid dynamics design, to improve on its speed."""

def add_openfish_to_database(db_path='museum.db', use_kid_friendly=True):
    """
    Add OpenFish artifact to the database
    
    Args:
        db_path: Path to the museum database
        use_kid_friendly: If True, uses kid-friendly description. If False, uses technical description.
    """
    
    # Choose which description to use
    description = KID_FRIENDLY_DESCRIPTION if use_kid_friendly else TECHNICAL_DESCRIPTION
    
    # Artifact data
    artifact_data = {
        'title': 'OpenFish',
        'artist': 'Sander C. van den Berg, Rob B.N. Scharff, Zoltán Rusák, Jun Wu',
        'date_painted': '2022',
        'location_in_museum': '2_a',
        'size': '40 × 15 cm',
        'media': 'Sculpture',
        'description': description,
        'curator_words': CURATOR_WORDS
    }
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"✓ Connected to database: {db_path}")
        
        # Check if OpenFish already exists
        cursor.execute("SELECT id, title FROM artifacts WHERE title LIKE '%OpenFish%'")
        existing = cursor.fetchone()
        
        if existing:
            print(f"\n⚠️  WARNING: An artifact with similar title already exists!")
            print(f"   ID: {existing[0]}, Title: {existing[1]}")
            response = input("   Do you want to add it anyway? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("✗ Cancelled.")
                conn.close()
                return False
        
        # Insert the artifact
        cursor.execute("""
            INSERT INTO artifacts 
            (title, artist, date_painted, location_in_museum, size, media, description, curator_words)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            artifact_data['title'],
            artifact_data['artist'],
            artifact_data['date_painted'],
            artifact_data['location_in_museum'],
            artifact_data['size'],
            artifact_data['media'],
            artifact_data['description'],
            artifact_data['curator_words']
        ))
        
        conn.commit()
        artifact_id = cursor.lastrowid
        
        print(f"\n{'='*60}")
        print("✓ SUCCESS! OpenFish artifact added to database")
        print(f"{'='*60}")
        print(f"Artifact ID: {artifact_id}")
        print(f"Title: {artifact_data['title']}")
        print(f"Artist: {artifact_data['artist']}")
        print(f"Location: {artifact_data['location_in_museum']}")
        print(f"Description type: {'Kid-friendly' if use_kid_friendly else 'Technical'}")
        
        # Show total count
        cursor.execute("SELECT COUNT(*) FROM artifacts")
        total = cursor.fetchone()[0]
        print(f"\nTotal artifacts in database: {total}")
        print(f"{'='*60}\n")
        
        # Show what was added
        print("Description preview:")
        print(f"  {artifact_data['description'][:150]}...")
        print()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Error adding artifact: {e}")
        return False

def view_openfish_details(db_path='museum.db'):
    """View the OpenFish artifact details if it exists"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM artifacts WHERE title LIKE '%OpenFish%'")
        artifact = cursor.fetchone()
        
        if artifact:
            print("\n=== OpenFish Artifact Details ===")
            print(f"ID: {artifact[0]}")
            print(f"Title: {artifact[1]}")
            print(f"Artist: {artifact[2]}")
            print(f"Date: {artifact[3]}")
            print(f"Location: {artifact[4]}")
            print(f"Size: {artifact[5]}")
            print(f"Media: {artifact[6]}")
            print(f"\nDescription:\n{artifact[7]}")
            print(f"\nCurator's Words:\n{artifact[8]}")
        else:
            print("OpenFish artifact not found in database.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("OpenFish Artifact Database Addition")
    print("="*60)
    
    # Check if database exists
    if not os.path.exists('museum.db'):
        print("\n✗ Error: museum.db not found in current directory!")
        print("Please make sure you're in the correct directory.")
        sys.exit(1)
    
    print("\nThis script will add the OpenFish artifact to your database.")
    print("\nYou have two description options:")
    print("1. Kid-friendly (recommended for ages 7-10)")
    print("2. Technical (original description)")
    
    choice = input("\nWhich description would you like to use? (1 or 2): ").strip()
    
    use_kid_friendly = choice == '1' or choice == ''
    
    print(f"\nUsing {'kid-friendly' if use_kid_friendly else 'technical'} description...")
    
    # Add the artifact
    success = add_openfish_to_database(use_kid_friendly=use_kid_friendly)
    
    if success:
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Update enhanced_rag_openai.py:")
        print('   Add to artwork_patterns:')
        print('   "openfish": ["openfish", "open fish", "robot fish", "robotic fish"]')
        print()
        print("2. Update main.py:")
        print('   Add to artwork_keywords: "openfish", "robot fish"')
        print()
        print("3. Restart your services:")
        print("   make restart")
        print("="*60)
        
        # Optionally view the full details
        view_details = input("\nWould you like to view the full artifact details? (yes/no): ").strip().lower()
        if view_details in ['yes', 'y']:
            view_openfish_details()