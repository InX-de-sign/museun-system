# streaming_openai.py - Streaming text generation for faster responses
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from openai import AzureOpenAI
from config import load_azure_openai_config

logger = logging.getLogger(__name__)

class StreamingOpenAI:
    """Streaming OpenAI client for real-time text generation"""
    
    def __init__(self):
        self.config = load_azure_openai_config()
        self.client = AzureOpenAI(
            api_key=self.config.api_key,
            api_version=self.config.api_version,
            azure_endpoint=self.config.azure_endpoint
        )
        
        # UPDATED: Shorter, more direct prompts for kids
        self.system_prompts = {
            'basic_artifact': """You are Artie, a fun museum buddy for kids aged 7-10.
            KEEP IT SHORT: 1-2 sentences max per response!
            Use simple, understandable words for kids, try to be encouraging and inspiring.
            Provide conversational (no emojis), informative, engaging, inspiring and fun answers. """,
            
            'general_art': """You are Artie, an engaging museum buddy for kids 7-10!
            KEEP IT SHORT: 2-3 sentences max per response!
            Use simple, understandable words for kids, try to be encouraging and inspiring.
            Provide conversational (no emojis), informative, engaging, inspiring and fun answers. """,
        }

    async def stream_response(self, query: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Stream OpenAI response word by word"""
        try:
            # Determine query type and get appropriate system prompt
            query_type = context.get('query_type', 'general_art')
            system_prompt = self.system_prompts.get(query_type, self.system_prompts['general_art'])
            
            # Build short, focused prompt
            user_prompt = self._build_short_prompt(query, context)
            
            # Create streaming completion
            stream = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,  # REDUCED: Force shorter responses
                temperature=0.7,
                stream=True  # Enable streaming
            )
            
            logger.info("Starting streaming response...")
            
            # Stream each chunk
            accumulated_text = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_text += content
                    yield content
            
            logger.info(f"Streaming completed: {len(accumulated_text)} chars")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            # Fallback to short static response
            fallback = "That's so cool! What else would you like to know?"
            for char in fallback:
                yield char
                await asyncio.sleep(0.01)  # Simulate streaming

    def _build_short_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build focused prompt for short responses"""
        prompt_parts = []
        
        # Add essential context only
        detected_artifact = context.get('detected_artifact')
        if detected_artifact:
            prompt_parts.append(f"ARTWORK: {detected_artifact}")
        
        # Add brief local context if available
        local_db = context.get('local_database', '')
        if local_db and len(local_db) < 200:  # Only short context
            prompt_parts.append(f"INFO: {local_db[:200]}")
        
        prompt_parts.append(f"QUESTION: {query}")
        prompt_parts.append("RESPOND IN 1-2 SHORT SENTENCES ONLY!")
        
        return "\n".join(prompt_parts)

    async def get_short_response(self, query: str, context: Dict[str, Any]) -> str:
        """Get complete short response (non-streaming fallback)"""
        try:
            query_type = context.get('query_type', 'general_art')
            system_prompt = self.system_prompts.get(query_type, self.system_prompts['general_art'])
            user_prompt = self._build_short_prompt(query, context)
            
            response = self.client.chat.completions.create(
                model=self.config.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,  # Force short responses
                temperature=0.7
            )
            
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Short response error: {e}")
        
        return "That's awesome! What else would you like to explore?"