import logging
import weaviate
import pandas as pd
from typing import List, Dict, Any
from weaviate.weaviate_interface import WeaviateInterface


class WeaviateService:
    def __init__(self):
        self.wi = None

    async def initialize_weaviate(self, openai_key: str, weaviate_url: str, reset: bool = False) -> WeaviateInterface:
        print("===:> Initializing Weaviate")
        weaviate_interface = await weaviate.setup_weaviate_interface(openai_key, weaviate_url)
        if not (await weaviate_interface.schema.is_valid()) or reset:
            await weaviate_interface.schema.reset()

            # Load and insert products data
            products = pd.read_csv("data/clean_products.csv")
            products = products.drop(columns=["raw_data", "id", "raw_length"])
            products_data = products.to_dict(orient="records")

            # loop through the products in batches of 20
            for i in range(0, len(products_data), 20):
                try:
                    await weaviate_interface.product.batch_upsert(products_data[i : i + 20])
                except Exception as e:
                    print(f"Error inserting products at index {i}: {e}")

            chitchat_data = pd.read_csv("data/chitchat.csv")
            chitchat_prompts = chitchat_data["prompt"].tolist()

            political_data = pd.read_csv("data/politics.csv")
            political_prompts = political_data["prompt"].tolist()

            clear_intent_data = pd.read_csv("data/clear_intent.csv")
            clear_intent_prompts = clear_intent_data["prompt"].tolist()

            vague_intent_data = pd.read_csv("data/vague_intent.csv")
            vague_intent_prompts = vague_intent_data["prompt"].tolist()

            # Load and insert routes data
            routes_data = {
                "politics": political_prompts,
                "chitchat": chitchat_prompts,
                "clear_intent_product": clear_intent_prompts,
                "vague_intent_product": vague_intent_prompts,
            }

            for route, prompts in routes_data.items():
                route_data = [{"prompt": message, "route": route} for message in prompts]
                await weaviate_interface.route.batch_upsert(route_data)

        is_valid = await weaviate_interface.schema.is_valid()
        info = await weaviate_interface.schema.info()
        logging.info(f" Weaviate schema is valid: {is_valid}")
        logging.info(f" Weaviate schema info: {info}")

        self.wi = weaviate_interface

    async def search_routes(self, query: str) -> List[Dict[str, Any]]:
        routes = await self.wi.route.search(query, ["route"], limit=1)
        print(f"Found routes: {routes}")
        return routes[0].get("route")

    async def search_products(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            features = ["name", "size", "form", "processor", "memory", "io", "manufacturer", "summary"]
            products = await self.wi.product.search(query, features, limit)
            return products
        except Exception as e:
            print(f"Error in Weaviate search: {str(e)}")
            raise