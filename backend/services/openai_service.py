import tiktoken
import logging
from openai import AsyncOpenAI
from typing import List, Optional, Tuple, Dict, Any
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self, api_key: str, config: Config):
        self.client = AsyncOpenAI(api_key=api_key)
        self.config = config
        self.encoders = {}

    def _get_encoder(self, model: str):
        if model not in self.encoders:
            self.encoders[model] = tiktoken.encoding_for_model(model)
        return self.encoders[model]

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, int, int]:
        try:
            model = model or self.config.DEFAULT_MODEL
            logger.info(f"===> Using model: {model}")
            encoder = self._get_encoder(model)
            logger.info(f"===> Messages: {messages}")

            input_token_count = sum(len(encoder.encode(msg["content"])) for msg in messages)
            logger.info(f"Input token count: {input_token_count}")

            kwargs = {
                "model": model,
                "messages": messages,
                # "temperature": temperature or self.config.DEFAULT_TEMPERATURE,
                # "max_tokens": max_tokens or self.config.DEFAULT_MAX_TOKENS,
                # "top_p": top_p or self.config.DEFAULT_TOP_P,
                "temperature": temperature or self.config["DEFAULT_TEMPERATURE"],
                "max_tokens": max_tokens or self.config["DEFAULT_MAX_TOKENS"],
                "top_p": top_p or self.config["DEFAULT_TOP_P"],
                "stream": stream,
            }
            if functions:
                kwargs["functions"] = functions

            response = await self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            output_token_count = len(encoder.encode(content))
            # logger.info(f"Output token count: {output_token_count}")

            return content, input_token_count, output_token_count

        except Exception as e:
            logger.error(f"Error in OpenAI API call: {str(e)}")
            raise

    async def generate_response(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        formatted_chat_history: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> Tuple[str, int, int]:
        messages = self._prepare_messages(user_message, system_message, formatted_chat_history)
        return await self.create_chat_completion(messages, **kwargs)

    def _prepare_messages(
        self,
        user_message: str,
        system_message: Optional[str],
        formatted_chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        if formatted_chat_history and isinstance(formatted_chat_history, list):
            messages.extend(formatted_chat_history)

        messages.append({"role": "user", "content": user_message})
        return messages

    async def create_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        try:
            response = await self.client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error in creating embedding: {str(e)}")
            raise
