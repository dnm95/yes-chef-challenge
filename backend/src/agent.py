import json
import os
from openai import AsyncOpenAI
from .catalog import SyscoCatalog
from .models import LineItem

class ChefAgent:
    """
    The Core AI Logic.
    Uses OpenAI's Function Calling to interact with the Sysco Catalog.
    Implements a 'Reasoning Loop' to breakdown dishes into ingredients.
    """

    def __init__(self, catalog: SyscoCatalog):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.catalog = catalog

    async def estimate_item(self, menu_item: dict, learnings: str) -> LineItem:
        """
        Estimates the cost for a single menu item using RAG (Retrieval Augmented Generation).
        """
        
        # --- FIX: Inject the Pydantic Schema directly into the prompt ---
        # This prevents the LLM from hallucinating keys like 'ingredient' instead of 'name'
        schema_structure = json.dumps(LineItem.model_json_schema(), indent=2)

        system_prompt = f"""
        You are an expert Catering Estimator for 'Elegant Foods'.
        
        GLOBAL CONTEXT (Learnings from previous batches):
        {learnings}
        
        YOUR MISSION:
        1. Analyze the dish description.
        2. Break it down into specific ingredients.
        3. USE THE 'search_catalog' TOOL to find real pricing. 
           - Do not guess prices if you can search.
           - If the catalog returns a case price (e.g., $30 for 6 cans), calculate the unit cost for the portion.
        
        CRITICAL OUTPUT RULES (STRICT JSON COMPLIANCE):
        - You MUST output a JSON object that strictly matches this schema:
        {schema_structure}
        
        - 'item_name': Must match the input menu name exactly.
        - 'unit_cost': Must be a NUMBER (float) or null. NEVER output a string like "not_available" or "$5.00".
        - 'source': Must be exactly one of ["sysco_catalog", "estimated", "not_available"].
        """

        # Tool Definition (OpenAI Function Calling)
        tools = [{
            "type": "function",
            "function": {
                "name": "search_catalog",
                "description": "Search the Sysco supplier catalog for an ingredient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Name of ingredient (e.g. 'heavy cream')"}
                    },
                    "required": ["query"]
                }
            }
        }]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Estimate this item: {json.dumps(menu_item)}"}
        ]

        # --- Step 1: Reasoning & Tool Invocation ---
        response = await self.client.chat.completions.create(
            model="gpt-4.1", 
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        messages.append(msg)

        # --- Step 2: Tool Execution Loop ---
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.function.name == "search_catalog":
                    args = json.loads(tool_call.function.arguments)
                    
                    # Execute local Python search
                    search_results = self.catalog.search(args['query'])
                    
                    # Feed results back to the LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(search_results)
                    })

            # --- Step 3: Final JSON Generation ---
            # We enforce JSON mode again to ensure the schema injection works
            final_response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"}
            )
            raw_json = final_response.choices[0].message.content
            
            # Debugging: Print raw JSON if validation fails (helps troubleshooting)
            try:
                return LineItem.model_validate_json(raw_json)
            except Exception as e:
                print(f"❌ JSON Validation Failed for {menu_item.get('name')}")
                print(f"Raw Output: {raw_json}")
                raise e
        
        # Fallback if no tools were used
        try:
            return LineItem.model_validate_json(msg.content)
        except Exception as e:
             print(f"❌ JSON Validation Failed (No Tools) for {menu_item.get('name')}")
             print(f"Raw Output: {msg.content}")
             raise e

    async def compact_context(self, batch_results: list) -> str:
        """
        Implementation of 'Context Compaction'.
        """
        summary_input = [
            {
                "item": r.item_name, 
                "missing_ingredients": [i.name for i in r.ingredients if i.source != 'sysco_catalog']
            }
            for r in batch_results
        ]
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize new learnings about missing ingredients or catalog quirks in 2 sentences."},
                {"role": "user", "content": json.dumps(summary_input)}
            ]
        )
        return response.choices[0].message.content
