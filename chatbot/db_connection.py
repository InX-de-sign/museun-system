"""
PostgreSQL Database Connection Module for Zoo AI Chatbot
Replaces SQLite connections with PostgreSQL
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgreSQLConnection:
    """Handles PostgreSQL database connections for the zoo chatbot"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize PostgreSQL connection pool
        
        Parameters can be provided directly or via environment variables:
        - POSTGRES_HOST (default: localhost)
        - POSTGRES_PORT (default: 5432)
        - POSTGRES_DB (default: zoo_db)
        - POSTGRES_USER (default: postgres)
        - POSTGRES_PASSWORD
        """
        
        # Use provided values or environment variables or defaults
        self.host = host or os.getenv('POSTGRES_HOST', 'localhost')
        self.port = port or int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = database or os.getenv('POSTGRES_DB', 'zoo_db')
        self.user = user or os.getenv('POSTGRES_USER', 'postgres')
        self.password = password or os.getenv('POSTGRES_PASSWORD', '')
        
        # Create connection pool
        try:
            self.pool = SimpleConnectionPool(
                min_connections,
                max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"PostgreSQL connection pool created: {self.database}@{self.host}:{self.port}")
            self._test_connection()
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise
    
    def _test_connection(self):
        """Test the database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()
                    logger.info(f"PostgreSQL connection successful: {version[0][:50]}...")
                    return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Context manager for getting a connection from the pool"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error, rolling back: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """Context manager for getting a cursor"""
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, 
                     fetch_all: bool = False, dict_cursor: bool = True) -> Optional[Any]:
        """
        Execute a SQL query with parameters
        
        Args:
            query: SQL query string (use %s for parameters)
            params: Tuple of parameters
            fetch_one: Return single row
            fetch_all: Return all rows
            dict_cursor: Use dictionary cursor (RealDictCursor)
        
        Returns:
            Query results or None
        """
        try:
            with self.get_cursor(dict_cursor=dict_cursor) as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def insert(self, table: str, data: Dict[str, Any], returning: str = "id") -> Optional[int]:
        """
        Insert data into a table
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs
            returning: Column to return (default: id)
        
        Returns:
            The value of the returning column
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        if returning:
            query += f" RETURNING {returning}"
        
        try:
            if returning:
                result = self.execute_query(query, values, fetch_one=True)
                return result[returning] if result else None
            else:
                self.execute_query(query, values)
                return None
        except Exception as e:
            logger.error(f"Insert error: {e}")
            raise
    
    def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """
        Update data in a table
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs to update
            where: Dictionary of column: value pairs for WHERE clause
        
        Returns:
            Number of rows affected
        """
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
        
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = tuple(list(data.values()) + list(where.values()))
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, values)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Update error: {e}")
            raise
    
    def close(self):
        """Close all connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")


class ZooDatabase:
    """High-level database operations for zoo chatbot"""
    
    def __init__(self, db_connection: PostgreSQLConnection):
        self.db = db_connection
        logger.info("ZooDatabase initialized")
    
    # ==================== ANIMAL QUERIES ====================
    
    def get_animal_by_id(self, animal_id: str) -> Optional[Dict[str, Any]]:
        """Get animal by ID"""
        query = "SELECT * FROM animals WHERE animal_id = %s"
        return self.db.execute_query(query, (animal_id,), fetch_one=True)
    
    def search_animals_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search animals by common or scientific name"""
        query = """
            SELECT * FROM animals 
            WHERE LOWER(common_name) LIKE LOWER(%s) 
               OR LOWER(scientific_name) LIKE LOWER(%s)
            ORDER BY common_name
        """
        search_term = f"%{name}%"
        return self.db.execute_query(query, (search_term, search_term), fetch_all=True) or []
    
    def get_animals_by_zone(self, zone: str) -> List[Dict[str, Any]]:
        """Get all animals in a specific zone"""
        query = "SELECT * FROM animals WHERE LOWER(zone) = LOWER(%s) ORDER BY common_name"
        return self.db.execute_query(query, (zone,), fetch_all=True) or []
    
    def get_all_animals(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all animals, optionally limited"""
        query = "SELECT * FROM animals ORDER BY common_name"
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute_query(query, fetch_all=True) or []
    
    def enhanced_animal_search(self, message: str, animal_entity: str = None) -> Optional[Tuple]:
        """
        Enhanced search with better matching (similar to enhanced_artwork_search)
        Returns tuple format for backward compatibility with existing code
        """
        # Strategy 1: Direct entity match
        if animal_entity:
            query = """
                SELECT common_name, scientific_name, distribution_range, habitat,
                       characteristics, location_in_park, description, fun_facts,
                       diet, threats, conservation_message
                FROM animals 
                WHERE LOWER(common_name) LIKE LOWER(%s) 
                   OR LOWER(scientific_name) LIKE LOWER(%s)
                   OR LOWER(animal_id) LIKE LOWER(%s)
                LIMIT 1
            """
            search_term = f"%{animal_entity}%"
            result = self.db.execute_query(
                query, 
                (search_term, search_term, search_term), 
                fetch_one=True,
                dict_cursor=False
            )
            if result:
                return result
        
        # Strategy 2: Keyword-based search
        message_lower = message.lower()
        
        # Common animal keywords
        animal_keywords = {
            'capybara': ['capybara', 'largest rodent', 'water loving'],
            'red panda': ['red panda', 'bamboo', 'himalaya'],
            'giant panda': ['giant panda', 'panda', 'black and white'],
            'sloth': ['sloth', 'slow', 'upside down'],
            'arctic fox': ['arctic fox', 'white fox', 'tundra'],
            'walrus': ['walrus', 'tusk', 'marine'],
            'gentoo penguin': ['gentoo', 'penguin', 'fastest swimmer'],
            'harbour seal': ['harbour seal', 'seal', 'spotted']
        }
        
        # Find matching animal
        for animal_name, keywords in animal_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                query = """
                    SELECT common_name, scientific_name, distribution_range, habitat,
                           characteristics, location_in_park, description, fun_facts,
                           diet, threats, conservation_message
                    FROM animals 
                    WHERE LOWER(common_name) LIKE LOWER(%s)
                    LIMIT 1
                """
                result = self.db.execute_query(
                    query, 
                    (f"%{animal_name}%",), 
                    fetch_one=True,
                    dict_cursor=False
                )
                if result:
                    return result
        
        return None
    
    # ==================== USER QUERIES ====================
    
    def get_or_create_user(self, user_id: str, name: str = None, age_group: str = None) -> Dict[str, Any]:
        """Get existing user or create new one"""
        # Try to get existing user
        user = self.db.execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,),
            fetch_one=True
        )
        
        if user:
            # Update last_active
            self.db.execute_query(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user_id,)
            )
            return user
        else:
            # Create new user
            data = {
                'user_id': user_id,
                'name': name,
                'age_group': age_group,
                'last_active': 'CURRENT_TIMESTAMP'
            }
            self.db.insert('users', data)
            return self.db.execute_query(
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,),
                fetch_one=True
            )
    
    def update_user_interests(self, user_id: str, interests: List[str]):
        """Update user interests"""
        self.db.execute_query(
            "UPDATE users SET interests = %s WHERE user_id = %s",
            (interests, user_id)
        )
    
    def add_favorite_animal(self, user_id: str, animal_name: str):
        """Add an animal to user's favorites"""
        query = """
            UPDATE users 
            SET favorite_animals = array_append(
                COALESCE(favorite_animals, ARRAY[]::text[]), 
                %s
            )
            WHERE user_id = %s
            AND (favorite_animals IS NULL OR NOT (%s = ANY(favorite_animals)))
        """
        self.db.execute_query(query, (animal_name, user_id, animal_name))
    
    # ==================== CONVERSATION QUERIES ====================
    
    def log_conversation(self, user_id: str, message: str, response: str, 
                        detected_animal: str = None, context: Dict = None, 
                        session_id: str = None):
        """Log a conversation"""
        data = {
            'user_id': user_id,
            'session_id': session_id,
            'message': message,
            'response': response,
            'detected_animal': detected_animal,
            'context': Json(context) if context else None
        }
        return self.db.insert('conversations', data)
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        query = """
            SELECT * FROM conversations 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        return self.db.execute_query(query, (user_id, limit), fetch_all=True) or []
    
    # ==================== LEARNING PROGRESS QUERIES ====================
    
    def log_learning_progress(self, user_id: str, animal_id: str, 
                             interaction_type: str, duration: int = None,
                             quiz_score: float = None):
        """Log learning progress"""
        data = {
            'user_id': user_id,
            'animal_id': animal_id,
            'interaction_type': interaction_type,
            'duration': duration,
            'quiz_score': quiz_score
        }
        return self.db.insert('learning_progress', data)
    
    def get_user_learning_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user learning statistics"""
        query = """
            SELECT 
                COUNT(DISTINCT animal_id) as animals_learned,
                COUNT(*) as total_interactions,
                AVG(quiz_score) as avg_quiz_score,
                SUM(duration) as total_time_seconds
            FROM learning_progress
            WHERE user_id = %s
        """
        return self.db.execute_query(query, (user_id,), fetch_one=True)
    
    # ==================== ANIMAL ENCOUNTER QUERIES ====================
    
    def log_animal_encounter(self, user_id: str, animal_id: str, 
                            encounter_type: str, location: str = None,
                            duration: int = None):
        """Log when user encounters an animal"""
        data = {
            'user_id': user_id,
            'animal_id': animal_id,
            'encounter_type': encounter_type,
            'location': location,
            'duration': duration
        }
        return self.db.insert('animal_encounters', data)
    
    def get_user_encounters(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all animal encounters for a user"""
        query = """
            SELECT ae.*, a.common_name, a.zone
            FROM animal_encounters ae
            JOIN animals a ON ae.animal_id = a.animal_id
            WHERE ae.user_id = %s
            ORDER BY ae.timestamp DESC
        """
        return self.db.execute_query(query, (user_id,), fetch_all=True) or []


# Convenience function to create database connection
def create_zoo_database(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None
) -> ZooDatabase:
    """
    Create and return a ZooDatabase instance
    
    Usage:
        zoo_db = create_zoo_database()
        animals = zoo_db.get_all_animals()
    """
    pg_conn = PostgreSQLConnection(host, port, database, user, password)
    return ZooDatabase(pg_conn)


# Example usage and testing
if __name__ == "__main__":
    # Test the database connection
    try:
        print("Testing PostgreSQL Zoo Database Connection...")
        print("=" * 50)
        
        # Create connection
        zoo_db = create_zoo_database()
        
        # Test 1: Get all animals
        print("\n1. Getting all animals...")
        animals = zoo_db.get_all_animals(limit=3)
        for animal in animals:
            print(f"   - {animal['common_name']} ({animal['scientific_name']})")
        
        # Test 2: Search for specific animal
        print("\n2. Searching for 'panda'...")
        pandas = zoo_db.search_animals_by_name("panda")
        for panda in pandas:
            print(f"   - {panda['common_name']}: {panda['description'][:100]}...")
        
        # Test 3: Get animals by zone
        print("\n3. Getting animals in 'Ice Land'...")
        ice_animals = zoo_db.get_animals_by_zone("Ice Land")
        for animal in ice_animals:
            print(f"   - {animal['common_name']} at {animal['location_in_park']}")
        
        # Test 4: Enhanced search
        print("\n4. Testing enhanced search...")
        result = zoo_db.enhanced_animal_search("Tell me about capybaras", "capybara")
        if result:
            print(f"   Found: {result[0]}")
            print(f"   Description: {result[6][:100]}...")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()