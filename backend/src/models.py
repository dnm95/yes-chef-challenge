from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# ==========================================
# DATA MODELS (The "Contract")
# ==========================================
# We use Pydantic for two critical reasons:
# 1. Validation: It prevents the system from crashing due to bad data types.
# 2. LLM Steering: These models are converted to JSON Schemas and passed 
#  to OpenAI, forcing the model to output structured data (Function Calling).

class Ingredient(BaseModel):
  """
  Atomic unit of the quote. 
  Represents a single row in the ingredient cost breakdown.
  """
  # Field descriptions act as "Micro-Prompts" for the AI.
  name: str = Field(..., description="Ingredient name identified by the Agent")
  
  quantity: str = Field(..., description="Estimated quantity per serving (e.g., '2 oz', '1 each')")
  
  # We use Optional because sometimes pricing is impossible to find.
  unit_cost: Optional[float] = Field(None, description="Calculated cost for this specific quantity. Null if unavailable.")
  
  # Strict Enum: The AI CANNOT output anything other than these 3 values.
  # This ensures our Frontend UI logic (Green/Yellow/Red badges) always works.
  source: Literal["sysco_catalog", "estimated", "not_available"] = Field(
    ..., 
    description="Source of the pricing data. 'sysco_catalog' implies a direct match."
  )
  
  sysco_item_number: Optional[str] = Field(None, description="The unique ID from the Sysco catalog if matched.")

class LineItem(BaseModel):
  """
  Aggregates ingredients into a full Menu Item.
  """
  item_name: str = Field(..., description="Name of the dish as per the menu spec")
  
  category: str = Field(..., description="Menu category (e.g., appetizers, main_plates)")
  
  ingredients: List[Ingredient] = Field(..., description="List of component ingredients")
  
  # Calculated field: Sum of all ingredient.unit_cost
  ingredient_cost_per_unit: float = Field(..., description="Total summation of ingredient costs per serving")

class CateringQuote(BaseModel):
  """
  The Final Output.
  This matches the 'quote_schema.json' requirement provided in the challenge.
  """
  quote_id: str = Field(..., description="Unique identifier for this quote generation run")
  event: str = Field(..., description="Name of the event")
  
  # Auto-generates timestamp in ISO format with Z (UTC)
  generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
  
  line_items: List[LineItem]

# ==========================================
# STATE MANAGEMENT MODELS
# ==========================================

class JobState(BaseModel):
  """
  The 'Save Game' File.
  This model defines exactly what gets saved to 'job_state.json'.
  """
  processed_count: int = 0
  
  # We store the full list of processed LineItems here. 
  # This grows as the job progresses.
  processed_items: List[LineItem] = []
  
  # --- CONTEXT COMPACTION ---
  # This string holds the "memory" of the agent.
  # Instead of passing the full history of previous items (which costs tokens),
  # we only pass this summary string to the next batch.
  current_learnings: str = "None yet. Proceed with standard search."
  
  # Status flag to drive the Frontend UI loading state
  status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
