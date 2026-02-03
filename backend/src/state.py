import json
import os
from .models import JobState, LineItem

# --- CONFIGURATION ---
# We store the state in a local JSON file.
# In a production environment (Multi-tenant), this would be replaced by 
# a database connection (e.g., PostgreSQL or Redis) using a session_id.
STATE_FILE = os.path.join("data", "job_state.json")

class StateManager:
  """
  Persistence Layer.
  Responsible for saving the application state to disk and reloading it 
  if the server restarts. This satisfies the 'Resumability' requirement.
  """
  
  def __init__(self):
    # Initialize with a blank state
    self.state = JobState()
    # Immediately try to load existing data from disk (Crash Recovery)
    self.load_state()

  def load_state(self):
    """
    Deserialization Logic.
    Reads the JSON file and converts it back into Pydantic models.
    """
    if os.path.exists(STATE_FILE):
      try:
        with open(STATE_FILE, 'r') as f:
          data = json.load(f)
          # Pydantic Magic: Validate and parse raw JSON into a Python Object
          self.state = JobState(**data)
          print(f"🔄 State Resumed: {self.state.processed_count} items previously processed.")
      except Exception as e:
        # Fail-safe: If the file is corrupted, we start fresh rather than crashing app
        print(f"⚠️ Warning: Corrupted state file found. Starting fresh. Error: {e}")

  def save_state(self):
    """
    Serialization Logic.
    Dumps the current Python object memory into the JSON file.
    """
    try:
      with open(STATE_FILE, 'w') as f:
        # 'model_dump_json' is a Pydantic V2 method that creates a clean JSON string
        f.write(self.state.model_dump_json(indent=2))
    except Exception as e:
      print(f"❌ Critical Error: Failed to save state. {e}")

  def update_batch(self, new_items: list[LineItem], new_learnings: str):
    """
    Checkpointing.
    Called after every batch (3 items) finishes. 
    It updates the memory and immediately flushes to disk.
    """
    # 1. Add new results to the main list
    self.state.processed_items.extend(new_items)
    
    # 2. Update the counter (useful for progress bars)
    self.state.processed_count += len(new_items)
    
    # 3. Context Compaction / Accumulation
    # We append new learnings to the existing history.
    # The pipe '|' acts as a visual separator for the LLM in the next turn.
    self.state.current_learnings = f"{self.state.current_learnings} | {new_learnings}"
    
    # 4. Persist to disk immediately (Critical for fault tolerance)
    self.save_state()

  def get_processed_names(self):
    """
    Optimization for Resumability.
    Returns a Python 'Set' of names.
    Why a Set? Looking up items in a Set is O(1) (instant), 
    whereas looking up in a List is O(n) (slower as list grows).
    """
    return {item.item_name for item in self.state.processed_items}
  
  def clear_state(self):
    """
    Hard Reset.
    Deletes the persistent file. Used when the user clicks 'Start' 
    with a new menu, ensuring we don't mix old data with new data.
    """
    if os.path.exists(STATE_FILE):
      os.remove(STATE_FILE)
    self.state = JobState()
