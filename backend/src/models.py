from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# ==========================================
# DATA MODELS (Strict Typing)
# ==========================================
# These models enforce the structure defined in 'quote_schema.json'.
# We use Pydantic to validate data integrity at runtime, ensuring
# the LLM never returns malformed JSON.

class Ingredient(BaseModel):
  """
  Represents a single ingredient within a menu item.
  """
  name: str = Field(..., description="Ingredient name identified by the Agent")
  quantity: str = Field(..., description="Estimated quantity per serving (e.g., '2 oz', '1 each')")
  unit_cost: Optional[float] = Field(None, description="Calculated cost for this specific quantity. Null if unavailable.")
  source: Literal["sysco_catalog", "estimated", "not_available"] = Field(
    ..., 
    description="Source of the pricing data. 'sysco_catalog' implies a direct match."
  )
  sysco_item_number: Optional[str] = Field(None, description="The unique ID from the Sysco catalog if matched.")

class LineItem(BaseModel):
  """
  Represents a fully processed menu item with cost breakdown.
  """
  item_name: str = Field(..., description="Name of the dish as per the menu spec")
  category: str = Field(..., description="Menu category (e.g., appetizers, main_plates)")
  ingredients: List[Ingredient] = Field(..., description="List of component ingredients")
  ingredient_cost_per_unit: float = Field(..., description="Total summation of ingredient costs per serving")

class CateringQuote(BaseModel):
  """
  The final output structure representing the full quote.
  """
  quote_id: str = Field(..., description="Unique identifier for this quote generation run")
  event: str = Field(..., description="Name of the event")
  generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
  line_items: List[LineItem]

# ==========================================
# STATE MANAGEMENT MODELS
# ==========================================

class JobState(BaseModel):
  """
  Manages the persistence of the long-running job.
  Allows the system to recover from crashes/interruptions.
  """
  processed_count: int = 0
  processed_items: List[LineItem] = []
  # "Context Compaction": We store a summary of learnings (e.g., 'No Wagyu available')
  # to pass to future batches, preventing redundant searches.
  current_learnings: str = "None yet. Proceed with standard search."
  status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
