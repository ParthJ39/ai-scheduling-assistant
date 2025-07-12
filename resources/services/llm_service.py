import json
import requests
from logger import logger
from typing import Dict, List
from resources.config import llm_config


class LLMService:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_url = llm_config.base_url
        self.model_name = llm_config.model_name
        self.timeout = llm_config.timeout
        self.max_retries = llm_config.max_retries
        self.use_mock = llm_config.use_mock

    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        if self.use_mock:
            return self._mock_response(prompt)

        # Try local vLLM first
        try:
            return self._call_vllm(prompt, system_prompt, max_tokens)
        except Exception as e:
            logger.info(f"vLLM call failed: {e}")
            return self._mock_response(prompt)

    def _call_vllm(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Call LLM model running on vLLM server"""
        # Format prompt for Mixtral
        if system_prompt:
            formatted_prompt = f"<s>[INST] {system_prompt}\n\n{prompt} [/INST]"
        else:
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"

        payload = {
            "model": self.model_name,
            "prompt": formatted_prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["</s>", "[INST]", "[/INST]"]
        }

        response = requests.post(
            f"{self.base_url}/v1/completions",
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()
        result = response.json()

        return result['choices'][0]['text'].strip()


    def _mock_response(self, prompt: str) -> str:
        """Mock response when LLM services are unavailable"""
        prompt_lower = prompt.lower()

        # Email parsing responses
        if 'parse' in prompt_lower and 'email' in prompt_lower:
            return json.dumps({
                "suggested_date": "2025-07-17",
                "suggested_time": "13:00",
                "duration_minutes": 60,
                "urgency": "medium",
                "meeting_type": "other"
            })

        # Proposal evaluation responses
        elif 'evaluate' in prompt_lower and 'proposal' in prompt_lower:
            if 'userthree' in prompt_lower:
                return "This time conflicts with my lunch meeting with customers. I'd prefer an earlier or later slot."
            elif 'usertwo' in prompt_lower:
                return "This time works well for me. Good afternoon slot for productive discussions."
            else:
                return "This time slot works reasonably well with my schedule preferences."

        # Alternative suggestion responses
        elif 'alternative' in prompt_lower:
            return "This morning slot would be ideal for focused discussion before other meetings begin."

        # Negotiation responses
        elif 'negotiate' in prompt_lower or 'compromise' in prompt_lower:
            return "After analyzing all schedules, 3:00 PM provides the best balance for all participants."

        # Selection responses
        elif 'select' in prompt_lower or 'option' in prompt_lower:
            return "0"

        else:
            return "I understand your request and will process it accordingly."

    async def generate_async(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Async version of generate"""
        import asyncio

        # Run in a thread-pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate,
            prompt,
            system_prompt,
            max_tokens
        )
