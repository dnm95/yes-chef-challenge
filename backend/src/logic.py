import json
import os
from openai import AsyncOpenAI
from .catalog import SyscoCatalog
from .models import LineItem

class ChefAgent:
  """
  The AI Orchestrator.
  Uses OpenAI's GPT-4.1 (The smartest non-reasoning model of 2026) to 
  orchestrate ingredients and Function Calling (Tools) for catalog retrieval.
  """

  def __init__(self, catalog: SyscoCatalog):
    # Async client for high-concurrency non-blocking I/O
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
      raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
    self.client = AsyncOpenAI(api_key=api_key)
    self.catalog = catalog

  async def estimate_item(self, menu_item: dict, learnings: str) -> LineItem:
    """
    Core RAG Loop (Retrieval Augmented Generation):
    1. Receive Menu Item.
    2. LLM decides which ingredients to search for.
    3. Python executes searches against the CSV.
    4. LLM synthesizes final cost based on found vs estimated items.
    """
    
    # Inject the Pydantic JSON Schema directly into the prompt.
    # This guarantees the LLM output matches our internal data models perfectly.
    schema_structure = json.dumps(LineItem.model_json_schema(), indent=2)

    system_prompt = f"""
    You are an expert Catering Estimator for 'Elegant Foods' (US West Coast).
    
    GLOBAL CONTEXT (Learnings from previous batches):
    {learnings}
    
    YOUR MISSION:
    1. Analyze the dish description.
    2. Break it down into specific ingredients.
    3. USE THE 'search_catalog' TOOL to find real pricing in Sysco.
    
    PRICING STRATEGY (CRITICAL):
    - PRIORITY 1: Sysco Catalog. If found, calculate unit cost. Source = "sysco_catalog".
    - PRIORITY 2: Market Estimate. If NOT found (e.g. Wagyu, Truffles), ESTIMATE the cost. Source = "estimated".
    - PRIORITY 3: Not Available. Source = "not_available".
    
    CRITICAL OUTPUT RULES:
    - You MUST output a JSON object that strictly matches this schema:
    {schema_structure}
    """

    # Tool Definition (Function Calling Schema)
    tools = [{
      "type": "function",
      "function": {
        "name": "search_catalog",
        "description": "Search the Sysco supplier catalog for an ingredient.",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string", "description": "Name of ingredient"}
          },
          "required": ["query"]
        }
      }
    }]

    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": f"Estimate this item: {json.dumps(menu_item)}"}
    ]

    # --- STEP 1: REASONING ---
    # We use 'gpt-4.1'. It excels at instruction following 
    # and has a 1M token context window, perfect for RAG tasks.
    response = await self.client.chat.completions.create(
      model="gpt-4.1", 
      messages=messages,
      tools=tools,
      tool_choice="auto"
    )
    
    msg = response.choices[0].message
    messages.append(msg)

    # --- STEP 2: TOOL EXECUTION LOOP ---
    if msg.tool_calls:
      for tool_call in msg.tool_calls:
        if tool_call.function.name == "search_catalog":
          args = json.loads(tool_call.function.arguments)
          
          # Execute local Python search against CSV (RapidFuzz)
          # This uses the optimized search logic from catalog.py
          search_results = self.catalog.search(args['query'])
            
          messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(search_results)
          })

      # --- STEP 3: SYNTHESIS ---
      final_response = await self.client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        response_format={"type": "json_object"}
      )
      raw_json = final_response.choices[0].message.content
      
      return LineItem.model_validate_json(raw_json)
    
    return LineItem.model_validate_json(msg.content)

  async def compact_context(self, batch_results: list) -> str:
    """
    Context Compaction Logic.
    Summarizes results to identify 'Learnings' for the next batch.
    """
    summary_input = [
      {
        "item": r.item_name, 
        "missing_ingredients": [i.name for i in r.ingredients if i.source != 'sysco_catalog']
      }
      for r in batch_results
    ]
    
    response = await self.client.chat.completions.create(
      model="gpt-4.1",
      messages=[
        {"role": "system", "content": "Summarize new learnings about missing ingredients or catalog quirks in 2 sentences."},
        {"role": "user", "content": json.dumps(summary_input)}
      ]
    )
    return response.choices[0].message.content

  async def parse_menu_request(self, user_text: str) -> dict:
    """
    NLP Pipeline: Converts unstructured text to structured JSON Menu.
    """
    system_prompt = """
    You are a Catering Menu Architect.
    Convert the user's unstructured request into a structured JSON Menu Specification.
    """

    response = await self.client.chat.completions.create(
      model="gpt-4.1",
      messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
      ],
      response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
