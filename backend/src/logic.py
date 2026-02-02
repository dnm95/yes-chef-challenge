# backend/src/logic.py
import json
import os
import pandas as pd
from rapidfuzz import process, fuzz
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- Modelos de Datos (Schemas) ---
class Ingredient(BaseModel):
  name: str
  quantity: str
  unit_cost: Optional[float] = None
  source: Literal["sysco_catalog", "estimated", "not_available"]
  sysco_item_number: Optional[str] = None

class MenuItemCost(BaseModel):
  item_name: str
  category: str
  ingredients: List[Ingredient]
  ingredient_cost_per_unit: float

# --- Catálogo (Buscador) ---
class SyscoCatalog:
  def __init__(self, csv_path: str):
    # Leemos todo como string para evitar errores de tipo
    self.df = pd.read_csv(csv_path, dtype=str)
    # Pre-calculamos columna de búsqueda
    self.df['search_text'] = self.df['Product Description'] + " " + self.df['Brand']
    self.products = self.df.to_dict('records')
    self.search_keys = self.df['search_text'].tolist()

  def search(self, query: str, limit: int = 3):
    results = process.extract(query, self.search_keys, scorer=fuzz.WRatio, limit=limit)
    matches = []
    for text, score, idx in results:
      if score > 60:
        item = self.products[idx]
        matches.append({
          "sysco_id": item['Sysco Item Number'],
          "desc": item['Product Description'],
          "pack": item['Unit of Measure'],
          # Limpiamos el precio ($25.00 -> 25.00)
          "price_case": float(str(item['Cost']).replace('$', '').replace(',', '')),
          "match_score": score
        })
    return matches

# --- El Agente (Cerebro) ---
class ChefAgent:
  def __init__(self, catalog: SyscoCatalog):
    self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    self.catalog = catalog

  async def estimate_item(self, menu_item: dict) -> MenuItemCost:
    system_prompt = """
    Eres un estimador de costos experto para 'Elegant Foods'.
    Tu tarea: Desglosar un platillo en ingredientes y calcular su costo unitario usando el catálogo Sysco.
    
    Pasos:
    1. Identifica los ingredientes necesarios.
    2. USA LA TOOL 'search_catalog' para buscar precios reales.
    3. Calcula el costo por porción basado en el precio de la caja (Case Price) y tamaño (Pack Size).
    4. Si no encuentras algo, márcalo como 'estimated' o 'not_available'.
    """
    
    tools = [{
      "type": "function",
      "function": {
        "name": "search_catalog",
        "description": "Busca un ingrediente en el catálogo de Sysco.",
        "parameters": {
          "type": "object",
          "properties": {"query": {"type": "string"}},
          "required": ["query"]
        }
      }
    }]

    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": f"Platillo: {json.dumps(menu_item)}"}
    ]

    # Primer hit al LLM
    response = await self.client.chat.completions.create(
      model="gpt-4.1",
      messages=messages,
      tools=tools,
      tool_choice="auto"
    )
    msg = response.choices[0].message
    messages.append(msg)

    # Loop de herramientas (Agent Loop)
    if msg.tool_calls:
      for tool_call in msg.tool_calls:
          if tool_call.function.name == "search_catalog":
            args = json.loads(tool_call.function.arguments)
            results = self.catalog.search(args['query'])
            messages.append({
              "role": "tool",
              "tool_call_id": tool_call.id,
              "content": json.dumps(results)
            })

      # Segundo hit para obtener el JSON final
      final_resp = await self.client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        response_format={"type": "json_object"}
      )
      return MenuItemCost.model_validate_json(final_resp.choices[0].message.content)
    
    return MenuItemCost.model_validate_json(msg.content)
