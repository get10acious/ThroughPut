import json
import logging
import time
from typing import List, Tuple, Dict, Any
from models.message import Message
from models.product import Product
from services.openai_service import OpenAIService
from services.query_processor import QueryProcessor
from services.weaviate_service import WeaviateService
from utils.response_formatter import ResponseFormatter
from prompts.prompt_manager import PromptManager
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class VagueIntentState(Dict[str, Any]):
    model_name: str = "gpt-4o"
    chat_history: List[Dict[str, str]]
    current_message: str
    semantic_search_query: str
    product_count: int
    search_results: List[Product]
    input_tokens: Dict[str, int] = {
        "query_generation": 0,
        "generate": 0,
    }
    output_tokens: Dict[str, int] = {
        "query_generation": 0,
        "generate": 0,
    }
    time_taken: Dict[str, float] = {
        "query_generation": 0.0,
        "search": 0.0,
        "generate": 0.0,
    }
    output: Dict[str, Any] = {}


class VagueIntentAgent:

    def __init__(
        self,
        weaviate_service: WeaviateService,
        query_processor: QueryProcessor,
        openai_service: OpenAIService,
        prompt_manager: PromptManager,
    ):
        self.weaviate_service = weaviate_service
        self.query_processor = query_processor
        self.openai_service = openai_service
        self.workflow = self.setup_workflow()
        self.prompt_manager = prompt_manager
        self.response_formatter = ResponseFormatter()

    def setup_workflow(self) -> StateGraph:
        workflow = StateGraph(VagueIntentState)

        workflow.add_node("query_generation", self.query_generation_node)
        workflow.add_node("product_search", self.product_search_node)
        workflow.add_node("response_generation", self.response_generation_node)

        workflow.add_edge("query_generation", "product_search")
        workflow.add_edge("product_search", "response_generation")
        workflow.add_edge("response_generation", END)

        workflow.set_entry_point("query_generation")

        return workflow.compile()

    async def query_generation_node(self, state: VagueIntentState) -> VagueIntentState:
        start_time = time.time()
        result, input_tokens, output_tokens = await self.query_processor.generate_semantic_search_query(
            state["current_message"], state["chat_history"], model=state["model_name"]
        )

        state["semantic_search_query"] = result["query"]
        state["product_count"] = result.get("product_count", 5)
        state["input_tokens"]["query_generation"] = input_tokens
        state["output_tokens"]["query_generation"] = output_tokens
        state["time_taken"]["query_generation"] = time.time() - start_time

        logger.info(f"Generated semantic search query: {state['semantic_search_query']}")
        logger.info(f"Number of products to search: {state['product_count']}")
        return state

    async def product_search_node(self, state: VagueIntentState) -> VagueIntentState:
        start_time = time.time()
        results = await self.weaviate_service.search_products(
            state["semantic_search_query"], limit=state["product_count"]
        )
        state["search_results"] = [Product(**result) for result in results]
        state["time_taken"]["search"] = time.time() - start_time

        logger.info(f"Found {len(state['search_results'])} products")
        return state

    async def response_generation_node(self, state: VagueIntentState) -> VagueIntentState:
        start_time = time.time()
        system_message, user_message = self.prompt_manager.get_vague_intent_response_prompt(
            state["current_message"],
            state["chat_history"],
            state["search_results"],
        )

        response, input_tokens, output_tokens = await self.openai_service.generate_response(
            user_message=user_message, system_message=system_message, temperature=0.1, model=state["model_name"]
        )

        state["input_tokens"]["generate"] = input_tokens
        state["output_tokens"]["generate"] = output_tokens
        state["time_taken"]["generate"] = time.time() - start_time

        metadata = {
            "semantic_search_query": state["semantic_search_query"],
            "product_count": state["product_count"],
            "input_token_usage": state["input_tokens"],
            "output_token_usage": state["output_tokens"],
            "time_taken": state["time_taken"],
        }

        state["output"] = self.response_formatter.format_response("vague_intent_product", response, metadata)

        logger.info(f"Generated response: {state['output']}")
        return state

    async def run(self, message: Message, chat_history: List[Message]) -> Tuple[str, Dict[str, Any]]:
        logger.info(f"Running vague intent agent with message: {message}")

        initial_state = VagueIntentState(
            model_name=message.model,
            chat_history=chat_history,
            current_message=message.content,
            search_results=[],
        )

        try:
            logger.info("Starting workflow execution")
            final_state = await self.workflow.ainvoke(initial_state)
            logger.info("Workflow execution completed")

            output = json.dumps(final_state["output"], indent=2)
            stats = {
                "input_token_usage": final_state["input_tokens"],
                "output_token_usage": final_state["output_tokens"],
                "time_taken": final_state["time_taken"],
            }

        except Exception as e:
            logger.error(f"Error during workflow execution: {str(e)}", exc_info=True)
            output = json.dumps(
                self.response_formatter.format_error_response("An unexpected error occurred during processing.")
            )
            stats = {
                "input_token_usage": {"total": 0},
                "output_token_usage": {"total": 0},
                "time_taken": {"total": 0},
            }

        return output, stats
