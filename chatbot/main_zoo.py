# main.py - MODIFIED FOR POSTGRESQL ZOO
from enhanced_rag_openai_postgres import EnhancedRAGWithOpenAI  # CHANGED
from db_connection import create_zoo_database  # NEW
from memory_tracker import HybridMemoryTracker
import asyncio
import os
import logging
import requests
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridZooAI:  # RENAMED from HybridMuseumAI
    """
    HYBRID: PostgreSQL Zoo Database + OpenAI Enhanced RAG
    - PostgreSQL database: zoo animals with conservation info
    - OpenAI: Low-confidence or advanced queries with local context
    - Direct path: User Query -> Memory Context -> Enhanced RAG -> Response
    """
    
    def __init__(self, openai_api_key=None, zoo_db=None):
        logger.info("Initializing Hybrid Zoo AI (PostgreSQL + OpenAI)...")
        
        # Initialize memory system
        self.memory = HybridMemoryTracker()
        logger.info("Memory system initialized")
        
        # Initialize PostgreSQL Zoo Database
        self.zoo_db = zoo_db or create_zoo_database()
        logger.info("PostgreSQL Zoo Database connected")
        
        # Initialize Enhanced RAG with OpenAI
        try:
            self.enhanced_rag = EnhancedRAGWithOpenAI(zoo_db=self.zoo_db)
            logger.info("Enhanced RAG + OpenAI initialized")
        except Exception as e:
            logger.error(f"Enhanced RAG failed: {e}")
            raise Exception("Enhanced RAG system required")
                
        logger.info("Hybrid Zoo AI ready!")
    
    async def detect_current_animal(self):
        """Call CV service to detect what animal user is looking at"""
        try:
            response = requests.get(
                "http://zoo_cv:8001/detect-current",
                timeout=10
            )
            
            if response.status_code == 200:
                cv_result = response.json()
                if cv_result["status"] == "found":
                    animal_label = cv_result["detection"]["label"]
                    confidence = cv_result["detection"]["confidence"]
                    
                    logger.info(f"CV detected: {animal_label} (confidence: {confidence})")
                    return animal_label
            
            return None
            
        except Exception as e:
            logger.error(f"CV service error: {e}")
            return None
    
    async def process_message(self, message_text, user_id="default_user", cv_detected_animal=None):
        try:
            logger.info(f"Processing: '{message_text[:50]}...' for user: {user_id}")
            
            message_lower = message_text.lower()

            # Check if user is explicitly asking about what they're looking at
            is_asking_about_current_view = any(phrase in message_lower for phrase in [
                "what am i looking at", "what's this", "what is this", "identify this",
                "tell me about this", "what animal is this", "what's this animal",
                "this animal", "the animal", "what creature"
            ])

            if is_asking_about_current_view and not cv_detected_animal:
                cv_detected_animal = await self.detect_current_animal()
                if cv_detected_animal:
                    logger.info(f"CV service returned: {cv_detected_animal}")
            
            # If CV detected an animal, prioritize that context
            if cv_detected_animal:
                logger.info(f"CV detection active: {cv_detected_animal}")
                detected_animal = cv_detected_animal
            else:
                detected_animal = self._detect_animal(message_text)

            conversation_context = self.memory.get_conversation_context(user_id)
            personalized_context = self.memory.get_personalized_context(user_id)
            
            # Adjust query type based on CV detection and user intent
            if is_asking_about_current_view and cv_detected_animal:
                query_type = 'cv_identified_animal'
            else:
                query_type = self._determine_query_type(message_text, conversation_context)

            full_context = {
                'local_database': self._get_relevant_animal_context(message_text, detected_animal),  
                'user_context': personalized_context,
                'detected_animal': detected_animal,
                'cv_detected': cv_detected_animal is not None,
                'asking_about_current_view': is_asking_about_current_view,
                'query_type': query_type,
                'conversation_history': conversation_context.get('recent_messages', [])
            }

            response = await self.enhanced_rag.process_query_with_openai(
                query=message_text,
                context=full_context,
                user_id=user_id
            )

            self.memory.track_interaction(
                user_id=user_id,
                message=message_text,
                response=response,
                intent=self._extract_intent(message_text),
                entities=self._extract_entities(message_text),
                source="zoo_rag_openai"
            )

            logger.info(f"Response generated: '{response[:50]}...'")             
            return response
                
        except Exception as e:
            logger.error(f"Processing error: {e}")
            return "I'm having some technical difficulties, but I'm still here to help with your animal questions!"

    def _determine_query_type(self, message_text, context):
        """Simplified query type determination"""
        message_lower = message_text.lower()
        
        # Check for advanced analysis keywords
        advanced_indicators = [
            "analyze", "compare", "explain", "why", "how does",
            "adaptation", "evolution", "behavior", "habitat"
        ]
        
        if any(indicator in message_lower for indicator in advanced_indicators):
            return 'advanced_animal'
        
        # Check for basic animal queries
        animal_keywords = ["panda", "capybara", "penguin", "sloth", "fox", "walrus", "seal"]
        basic_indicators = ["what is", "tell me about", "describe", "where is", "where can i find"]
        
        has_animal = any(keyword in message_lower for keyword in animal_keywords)
        has_basic = any(indicator in message_lower for indicator in basic_indicators)
        
        if has_animal and has_basic:
            return 'basic_animal'
        elif has_animal:
            return 'basic_animal'
        
        # Zoo info queries
        zoo_keywords = ["hours", "tickets", "price", "open", "restroom", "cafe", "activities"]
        if any(keyword in message_lower for keyword in zoo_keywords):
            return 'basic_zoo_info'
        
        # Default to general wildlife knowledge
        return 'general_wildlife'

    def _detect_animal(self, message_text):
        """Detect which animal the user is asking about"""
        return self.enhanced_rag.extract_animal_from_message(message_text)

    def _get_relevant_animal_context(self, message_text, detected_animal=None):
        """Get relevant content from PostgreSQL zoo database"""
        try:
            # Try to find relevant animal using enhanced search
            animal_entity = detected_animal or self._detect_animal(message_text)
            
            if animal_entity:
                logger.info(f"Searching database for: {animal_entity}")

            result = self.enhanced_rag.enhanced_animal_search(message_text, animal_entity)
            
            if result:
                common_name, scientific_name, distribution, habitat, characteristics, \
                location, description, fun_facts, diet, threats, conservation = result
                
                return f"""ZOO ANIMAL INFORMATION:
                    Common Name: {common_name or 'Unknown'}
                    Scientific Name: {scientific_name or 'Unknown'}
                    Habitat: {habitat or 'Unknown'}
                    Location in Zoo: {location or 'Unknown'}
                    Description: {description or 'No description available'}
                    Fun Facts: {fun_facts or 'No fun facts available'}
                    Diet: {diet or 'Unknown diet'}
                    Conservation: {conservation or 'No conservation info'}"""
            
            # Fallback: general collection info
            animals = self.zoo_db.get_all_animals(limit=3)
            
            if animals:
                context_parts = ["ZOO COLLECTION OVERVIEW:"]
                for animal in animals:
                    common_name = animal.get('common_name', 'Unknown')
                    scientific_name = animal.get('scientific_name', 'Unknown')
                    description = (animal.get('description', 'No description'))[:100]
                    context_parts.append(f"- {common_name} ({scientific_name}): {description}...")
                
                return "\n".join(context_parts)
            
            return "Zoo collection information unavailable."
                
        except Exception as e:
            logger.error(f"Database context error: {e}")
            return "Local database context unavailable due to error."

    def _extract_intent(self, message_text):
        """Simple intent extraction for memory tracking"""
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return "greet"
        elif any(word in message_lower for word in ["hours", "open", "time"]):
            return "ask_hours"
        elif any(word in message_lower for word in ["price", "ticket", "cost"]):
            return "ask_pricing"
        elif any(word in message_lower for word in ["where", "location", "find"]):
            return "locate_animal"
        elif any(word in message_lower for word in ["analyze", "compare", "why"]):
            return "advanced_analysis"
        elif any(word in message_lower for word in ["panda", "capybara", "penguin"]):
            return "animal_info"
        else:
            return "general_query"

    def _extract_entities(self, message_text):
        """Simple entity extraction for memory tracking"""
        entities = []
        message_lower = message_text.lower()
        
        # Detect animals
        animals = {
            "capybara": "Capybara",
            "red panda": "Red Panda",
            "giant panda": "Giant Panda",
            "panda": "Giant Panda",
            "sloth": "Sloth",
            "arctic fox": "Arctic Fox",
            "fox": "Arctic Fox",
            "walrus": "Walrus",
            "penguin": "Gentoo Penguin",
            "seal": "Harbour Seal"
        }
        
        for key, name in animals.items():
            if key in message_lower:
                entities.append({"entity": "animal", "value": name})
        
        # Detect animal from RAG
        animal = self._detect_animal(message_text)
        if animal and not any(e.get('value') == animal for e in entities):
            entities.append({"entity": "animal", "value": animal})
        
        return entities

    def get_user_insights(self, user_id):
        """Get insights about user for personalization"""
        return self.memory.get_memory_summary(user_id)

# For backward compatibility
ZooAIAssistant = HybridZooAI

# Test the simplified system
async def test_zoo_system():
    """Test the zoo AI system"""
    print("Testing Zoo AI System")
    print("=" * 50)
    
    assistant = HybridZooAI()
    user_id = "test_user"
    
    test_queries = [
        "Hello!",
        "What are your hours?",
        "Tell me about capybaras",
        "Where can I find penguins?",
        "What do pandas eat?",
        "Why do arctic foxes change color?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        try:
            response = await assistant.process_message(query, user_id)
            print(f"   Response: {response[:100]}...")
            
            # Check memory
            context = assistant.memory.get_conversation_context(user_id)
            print(f"   Memory: {len(context.get('recent_messages', []))} messages")
                  
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\nZoo system test completed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_zoo_system())