from typing import Any, Dict, List, Optional
from weaviate_interface.services.base_service import BaseService
from weaviate_interface.weaviate_client import WeaviateClient
from weaviate.classes.query import Filter


class ProductService(BaseService):
    """
    Service for interacting with Product objects in Weaviate.
    """

    def __init__(self, client: WeaviateClient):
        super().__init__(client, "Product")

    def get_properties(self) -> List[str]:
        return [
            "product_id",
            "name",
            "manufacturer",
            "form_factor",
            "evaluation_or_commercialization",
            "processor_architecture",
            "processor_core_count",
            "processor_manufacturer",
            "processor_tdp",
            "memory",
            "onboard_storage",
            "input_voltage",
            "io_count",
            "wireless",
            "operating_system_bsp",
            "operating_temperature_max",
            "operating_temperature_min",
            "certifications",
            "price",
            "stock_availability",
            "lead_time",
            "short_summary",
            "full_summary",
            "full_product_description",
            "target_applications",
            "duplicate_ids",
        ]

    async def query_products(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query products with filtering and sorting capabilities.

        Args:
            filters: Dictionary of field-value pairs for filtering
            sort_field: Field to sort by
            sort_order: Sort direction ('asc' or 'desc')
            limit: Maximum number of results to return

        Returns:
            List of matching products
        """
        try:
            # Convert filters to Weaviate format
            weaviate_filter = None
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    filter_conditions.append(Filter.by_property(key).equal(value))
                weaviate_filter = (
                    Filter.all_of(filter_conditions) if len(filter_conditions) > 1 else filter_conditions[0]
                )

            # Get sorted results
            results = await self.get_sorted(
                limit=limit,
                filters=weaviate_filter,
                sort_by=sort_field,
                sort_order=sort_order,
                return_properties=self.get_properties(),
            )

            return results

        except Exception as e:
            logger.error(f"Error querying products: {e}")
            raise
