from typing import Dict, List
from models.message import Message
from generators.agent_v1 import AgentV1
from services.openai_service import OpenAIService
from services.weaviate_service import WeaviateService


class SemanticRouterV1:
    def __init__(
        self,
        openai_service: OpenAIService,
        weaviate_service: WeaviateService,
        agent_v1: AgentV1,
    ):
        self.openai_service = openai_service
        self.weaviate_service = weaviate_service
        self.agent_v1 = agent_v1

    async def run(self, message: Message, chat_history: List[Dict[str, str]]):
        route = await self.determine_route(message.content)
        return await self.handle_route(route, message, chat_history)

    async def determine_route(self, query: str) -> str:
        routes = await self.weaviate_service.search_routes(query)
        if not routes:
            raise Exception(f"No route found for query: {query}")
        print(f"Found routes: {routes}")
        return routes

    async def handle_route(self, route: str, message: Message, chat_history: List[Dict[str, str]]):
        if route == "politics":
            return '{"message": "I\'m sorry, I\'m not programmed to discuss politics."}', {
                "input_token_count": 0,
                "output_token_count": 0,
            }
        elif route == "chitchat":
            return await self.handle_chitchat(message, chat_history)
        elif route == "vague_intent_product":
            return await self.handle_vague_intent(message, chat_history)
        elif route == "clear_intent_product":
            return await self.agent_v1.run(message, chat_history)
        else:
            raise Exception(f"Unknown route: {route}")

    async def handle_chitchat(self, message: Message, chat_history: List[Dict[str, str]]):
        system_message = "You are ThroughPut assistant.  Your main task is to help users with their queries about products. The user is engaging in casual conversation with you. Respond naturally and politely to the user's message."
        response, input_tokens, output_tokens = await self.openai_service.generate_response(
            user_message=message.content,
            system_message=system_message,
            formatted_chat_history=chat_history,
            model=message.model,
        )
        return response, {"input_token_count": input_tokens, "output_token_count": output_tokens}

    async def handle_vague_intent(self, message: Message, chat_history: List[Dict[str, str]]):
        context = await self.weaviate_service.search_products(message.content)
        system_message = self._get_system_message_with_context(context)
        response, input_tokens, output_tokens = await self.openai_service.generate_response(
            user_message=message.content,
            system_message=system_message,
            formatted_chat_history=chat_history,
            model=message.model,
        )
        return response, {"input_token_count": input_tokens, "output_token_count": output_tokens}

    def _get_system_message_with_context(self, context: str) -> str:
        return f"""You are ThroughPut assistant. Your main task is to help users with their queries about products. Always respond in JSON format.
               The context that is provided is product data, in the form of name, size, form, processor, core, frequency, memory, voltage, io, thermal, feature, type, specification, manufacturer, location, description, and summary.
               In your response, synthesize the information from the context into a clear, simple, and easy-to-understand response to the user.
               Use the following context: {context}

               Make sure your response is in a JSON format with the following structure:
               {{
                   "response_description": "A concise description of the products that match the user's query.",
                   "response_justification": "Explanation of why this response is appropriate.",
                   "products": [
                       {{
                           "name": "Product Name",
                           "form": "Product Form Factor",
                           "processor": "Product Processor",
                           "memory": "Product Memory",
                           "io": "Product I/O",
                           "manufacturer": "Product Manufacturer",
                           "size": "Product Size",
                           "summary": "Product Summary"
                       }},
                       // ... more products if applicable
                   ],
                   "additional_info": "Any additional information or suggestions for the user"
               }}
        """
