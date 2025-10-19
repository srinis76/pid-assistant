"""
Query Router for P&ID Digital Assistant

Routes queries to either RAG or Vision engine based on query type.
Uses simple keyword-based routing for MVP.
"""

from typing import Literal

QueryType = Literal["rag", "vision"]


class QueryRouter:
    """Simple keyword-based query router"""

    def __init__(self):
        # Visual keywords that trigger vision path
        self.vision_keywords = [
            "show", "display", "where", "locate", "location",
            "flow", "path", "diagram", "layout",
            "picture", "image", "visual", "see", "view",
            "connected", "connection", "upstream", "downstream",
            "route", "routing", "piping", "inflow", "outflow"
        ]

        print(f"🔀 Query Router initialized")
        print(f"   Vision keywords: {len(self.vision_keywords)}")
        print()

    def route_query(self, query: str) -> QueryType:
        """
        Route query based on keywords

        Args:
            query: User's natural language query

        Returns:
            "vision" if visual query, "rag" otherwise
        """
        query_lower = query.lower()

        # Check for visual keywords
        for keyword in self.vision_keywords:
            if keyword in query_lower:
                return "vision"

        # Default to RAG (cheaper, faster)
        return "rag"

    def route_with_explanation(self, query: str) -> tuple[QueryType, str]:
        """
        Route query and explain the decision

        Returns:
            Tuple of (route, explanation)
        """
        query_lower = query.lower()

        # Check for visual keywords
        for keyword in self.vision_keywords:
            if keyword in query_lower:
                return "vision", f"Keyword '{keyword}' detected → routing to Vision"

        # Default to RAG
        return "rag", "No visual keywords detected → routing to RAG"


# Test function
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Testing Query Router")
    print("="*60 + "\n")

    # Initialize router
    router = QueryRouter()

    # Test queries
    test_queries = [
        "What is V-101?",
        "Show me where V-101 is located",
        "What are the operating conditions for the separator?",
        "Display the flow path from V-101 to C-104",
        "Tell me about PSV-101",
        "Where is the compressor connected?",
        "What's the design pressure of V-102?",
        "Show me the diagram of the gas processing system"
    ]

    print("Testing routing decisions:\n")

    for query in test_queries:
        route, explanation = router.route_with_explanation(query)
        icon = "🖼️" if route == "vision" else "📝"

        print(f"{icon} Query: \"{query}\"")
        print(f"   Route: {route.upper()}")
        print(f"   Reason: {explanation}")
        print()

    print("="*60)
    print("✅ Query Router test complete!")
    print("="*60 + "\n")
