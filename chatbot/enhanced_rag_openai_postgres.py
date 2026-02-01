# enhanced_rag_openai_postgres.py - Modified for PostgreSQL Zoo Database
from openai import AzureOpenAI
import os
import logging
import re
from typing import Dict, Any, Optional
import asyncio
from config import load_azure_openai_config
from db_connection import create_zoo_database, ZooDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRAGWithOpenAI:
    """Enhanced RAG system for Zoo AI with PostgreSQL"""
    
    def __init__(self, zoo_db: ZooDatabase = None):
        logger.info("Initializing Enhanced RAG with Azure OpenAI + PostgreSQL Zoo Database...")
        
        # Load Azure OpenAI configuration
        self.config = load_azure_openai_config()
        
        # Initialize Azure OpenAI client
        self.openai_client = AzureOpenAI(
            api_key=self.config.api_key,
            api_version=self.config.api_version,
            azure_endpoint=self.config.azure_endpoint
        )
        
        self.openai_available = True
        logger.info("Azure OpenAI client initialized")

        # PostgreSQL Zoo Database
        self.zoo_db = zoo_db or create_zoo_database()
        logger.info("PostgreSQL Zoo Database connected")

        # Animal patterns for entity extraction
        self.animal_patterns = {
            "capybara": ["capybara", "largest rodent", "water loving rodent"],
            "red panda": ["red panda", "ailurus"],
            "giant panda": ["giant panda", "panda", "ailuropoda"],
            "southern two-toed sloth": ["sloth", "two-toed sloth", "choloepus"],
            "arctic fox": ["arctic fox", "white fox", "vulpes lagopus"],
            "pacific walrus": ["walrus", "odobenus"],
            "gentoo penguin": ["gentoo penguin", "gentoo", "pygoscelis papua"],
            "harbour seal": ["harbour seal", "harbor seal", "phoca vitulina"]
        }

        # System prompts for different query types (adapted for zoo)
        self.system_prompts = {
            'basic_animal': """You are Zoe, a fun and excited zoo buddy for kids aged 7-10! 
            You're talking to kids who might be new to animals or just curious about wildlife.
            Provide easy to understand, conversational (no emojis), fun, clear information about animals and exhibits.
            Keep it to 1-2 short, exciting and informative sentences.
            SPEAKING STYLE:
            - Compare things to stuff kids know (like pets, cartoons, their favorite animals)
            - Make it interactive and fun!
            Examples:
            "If you could be this animal for a day, what would you do first?"
            "What's the coolest animal you've ever seen?"
            Be like talking to your best friend who loves animals! Make them say "WOW!" and want to see more!
            Remember to keep the answers short, and using words kids 7-9 understand.""",
            
            'advanced_animal': """You are Zoe, an animal detective zoo buddy for curious kids aged 7-10! 
            Provide easy to understand, conversational (no emojis), fun, clear, factual information about animals.
            Keep it to 2-3 short, exciting and informative sentences.
            SPEAKING STYLE:
            - Break big ideas into fun, bite-sized pieces
            - Compare to things they experience: feelings, games, stories they know
            - Provide deeper analysis of animal adaptations and behaviors with easy terms for kids
            Remember to keep the answers short, and using words kids 7-9 understand.""",
            
            'general_wildlife': """You are Zoe, a super fun and excited zoo buddy for kids aged 7-10. 
            You're talking to kids who might be new to wildlife or just curious.
            Provide easy to understand, conversational (no emojis), fun, clear, factual information about animals.
            Keep it to 1-2 short, exciting and informative sentences.
            YOUR JOB:
            - Connect wildlife to their world: school, home, pets, favorite shows
            - Share interesting facts about animals and conservation
            - Provide practical zoo information (hours, locations, activities)
            - Explain wildlife concepts in age-appropriate language
            Examples:
            - "If you could help save any animal, which one would it be?"
            - "Want to try a fun animal challenge at home?"
            Remember to keep the answers short, and using words kids 7-9 understand."""
        }

        # Test OpenAI connection
        self._test_connection()
        logger.info("Enhanced RAG with PostgreSQL Zoo Database ready!")

    def _test_connection(self):
        """Test Azure OpenAI connection"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.deployment_name,  
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            logger.info("Azure OpenAI connection successful")
            return True
        except Exception as e:
            logger.error(f"Azure OpenAI connection failed: {e}")
            self.openai_available = False
            return False

    # Entity extraction for animals
    def extract_animal_from_message(self, message):
        """Extract animal names from message using specific animal patterns"""
        message_lower = message.lower()
        
        # Check for exact matches first
        for official_name, variations in self.animal_patterns.items():
            if official_name in message_lower:
                return official_name
            
            # Check variations
            for variation in variations:
                if variation in message_lower:
                    return official_name
        
        return None

    def enhanced_animal_search(self, message, animal_entity=None):
        """
        Enhanced search using PostgreSQL database
        Returns tuple format for backward compatibility
        """
        try:
            result = self.zoo_db.enhanced_animal_search(message, animal_entity)
            return result
        except Exception as e:
            logger.error(f"Animal search error: {e}")
            return None

    def build_contextual_response(self, animal_data, query):
        """Build contextual response from animal data"""
        if not animal_data:
            return None
        
        # Unpack the tuple (similar to old artwork format)
        common_name, scientific_name, distribution, habitat, characteristics, \
        location, description, fun_facts, diet, threats, conservation = animal_data
        
        query_lower = query.lower()
        
        # Build response based on query type
        if any(word in query_lower for word in ['where', 'find', 'location', 'see']):
            return f"{common_name} can be found at {location}! They live in {habitat} in the wild. Come visit them!"
        
        elif any(word in query_lower for word in ['eat', 'food', 'diet']):
            return f"{common_name}s eat {diet}. {fun_facts[:100] if fun_facts else ''}"
        
        elif any(word in query_lower for word in ['fun', 'cool', 'interesting', 'fact']):
            return f"Here's something cool about {common_name}s: {fun_facts[:150] if fun_facts else description[:150]}!"
        
        elif any(word in query_lower for word in ['save', 'protect', 'conservation', 'endangered', 'help']):
            threat_msg = f"They face threats like {threats}. " if threats else ""
            conservation_msg = conservation if conservation else "We can help by learning about them and protecting their habitat!"
            return f"{threat_msg}{conservation_msg}"
        
        else:
            # General description
            return f"{description[:200]}... {fun_facts[:100] if fun_facts else ''}"

    async def process_query_with_openai(self, query: str, context: Dict[str, Any], 
                                       user_id: str) -> str:
        """Process query using OpenAI with context from PostgreSQL database"""
        
        if not query or not isinstance(query, str):
            return "Welcome to our zoo! I'm Zoe, your animal buddy! What animal would you like to learn about?"
        
        # Determine query type
        query_type = context.get('query_type', 'general_wildlife')
        
        # Map query types to system prompts
        prompt_mapping = {
            'basic_local_artifact': 'basic_animal',  # For compatibility
            'basic_animal': 'basic_animal',
            'advanced_local_artifact': 'advanced_animal',  # For compatibility
            'advanced_animal': 'advanced_animal',
            'cv_identified_artifact': 'basic_animal',  # For compatibility
            'general_art_knowledge': 'general_wildlife',  # For compatibility
            'general_wildlife': 'general_wildlife'
        }
        
        system_prompt = self.system_prompts.get(
            prompt_mapping.get(query_type, 'general_wildlife'),
            self.system_prompts['general_wildlife']
        )
        
        # Build enhanced prompt with context
        user_prompt = self._build_enhanced_prompt(query, context)
        
        # Try OpenAI first
        if self.openai_available:
            response = await self._call_openai_api(system_prompt, user_prompt)
            if response:
                # Log conversation to database
                try:
                    detected_animal = context.get('detected_animal')
                    self.zoo_db.log_conversation(
                        user_id=user_id,
                        message=query,
                        response=response,
                        detected_animal=detected_animal,
                        context=context
                    )
                except Exception as e:
                    logger.error(f"Failed to log conversation: {e}")
                
                return response
        
        # Fallback to local enhanced response
        return self._generate_enhanced_local_fallback(query, context)

    def _build_enhanced_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build comprehensive prompt with all available context"""
        prompt_parts = []

        # Add CV/visual detection context
        try:
            if context.get('cv_detected') and context.get('detected_animal'):
                detected_animal = context.get('detected_animal')
                prompt_parts.append("IMPORTANT CONTEXT:")
                prompt_parts.append(f"The child is currently viewing: {detected_animal}")
                prompt_parts.append("Always refer to THIS animal when they say 'this animal', 'this one', or ask about details.")
                prompt_parts.append("")
        except Exception as e:
            logger.debug(f"CV context error: {e}")

        # Add zoo database context
        try:
            local_db = context.get('local_database') if context else None
            if local_db and isinstance(local_db, str) and local_db.strip():
                prompt_parts.append("ZOO ANIMAL INFORMATION:")
                prompt_parts.append(local_db)
                prompt_parts.append("")
        except Exception as e:
            logger.debug(f"Local database context error: {e}")
        
        # Add user preferences
        try:
            user_context = context.get('user_context') if context else None
            if user_context and isinstance(user_context, str) and user_context.strip():
                prompt_parts.append("CHILD'S INTERESTS:")
                prompt_parts.append(user_context)
                prompt_parts.append("")
        except Exception as e:
            logger.debug(f"User context error: {e}")
        
        # Add specific animal focus if detected
        try:
            detected_animal = context.get('detected_animal') if context else None
            if detected_animal and isinstance(detected_animal, str) and detected_animal.strip():
                prompt_parts.append(f"PRIMARY FOCUS: {detected_animal}")
                prompt_parts.append("")
        except Exception as e:
            logger.debug(f"Detected animal error: {e}")
        
        # Add the actual user query
        if query and isinstance(query, str):
            prompt_parts.append("CHILD'S QUESTION:")
            prompt_parts.append(query)
            prompt_parts.append("")
        
        return "\n".join(prompt_parts) if prompt_parts else f"CHILD'S QUESTION: {query}"

    async def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call OpenAI API with error handling"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model=self.config.deployment_name,  
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=self.config.max_tokens,  
                    temperature=self.config.temperature
                )
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            self.openai_available = False
            return None

    def _generate_enhanced_local_fallback(self, query: str, context: Dict[str, Any]) -> str:
        """Enhanced fallback response using database"""
        
        if not query or not isinstance(query, str):
            return "Welcome to our zoo! I'm Zoe, your animal buddy! What would you like to explore today?"
        
        # Try enhanced local search first
        animal_entity = self.extract_animal_from_message(query)
        result = self.enhanced_animal_search(query, animal_entity)
        
        if result:
            response = self.build_contextual_response(result, query)
            if response:
                return response
        
        # Use enhanced fallback patterns
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['panda', 'giant panda']):
            return "Giant pandas are adorable! They eat bamboo all day and love to climb trees. Want to learn more about them?"
        
        elif any(word in query_lower for word in ['capybara', 'largest rodent']):
            return "Capybaras are the world's largest rodents and they love swimming! They're super friendly and social animals."
        
        elif any(word in query_lower for word in ['penguin', 'gentoo']):
            return "Gentoo penguins are the fastest swimming birds! They can zoom through water at 36 km/h. Amazing!"
        
        elif any(word in query_lower for word in ['hello', 'hi', 'hey']):
            return "Hello there, young explorer! Welcome to our amazing zoo! I'm Zoe, your animal buddy. What's your name? What animal would you like to meet today?"
        
        else:
            return "Our zoo has so many amazing animals from around the world! We have pandas, penguins, sloths, and more. What animal interests you most?"


# Testing
async def test_enhanced_rag_postgres():
    """Test the enhanced RAG with PostgreSQL"""
    print("Testing Enhanced RAG with PostgreSQL Zoo Database")
    print("=" * 50)
    
    try:
        rag = EnhancedRAGWithOpenAI()
        
        test_queries = [
            {
                'query': "Tell me about capybaras",
                'context': {
                    'query_type': 'basic_animal',
                    'detected_animal': 'capybara'
                }
            },
            {
                'query': "Where can I find penguins?",
                'context': {
                    'query_type': 'basic_animal'
                }
            },
            {
                'query': "What do pandas eat?",
                'context': {
                    'query_type': 'basic_animal',
                    'detected_animal': 'giant panda'
                }
            }
        ]
        
        for i, test in enumerate(test_queries, 1):
            print(f"\n{i}. Testing: {test['query']}")
            
            # Get database context
            animal_entity = rag.extract_animal_from_message(test['query'])
            result = rag.enhanced_animal_search(test['query'], animal_entity)
            
            if result:
                print(f"   Found animal: {result[0]}")
                
                # Build context
                context = test['context'].copy()
                context['local_database'] = f"""ZOO ANIMAL INFORMATION:
                    Common Name: {result[0]}
                    Scientific Name: {result[1]}
                    Habitat: {result[3]}
                    Location in Zoo: {result[5]}
                    Description: {result[6]}
                    Fun Facts: {result[7]}"""
                
                response = await rag.process_query_with_openai(
                    test['query'], 
                    context, 
                    "test_user"
                )
                print(f"   Response: {response[:200]}...")
            else:
                print(f"   No animal found in database")
        
        print("\n✅ Enhanced RAG PostgreSQL test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_enhanced_rag_postgres())