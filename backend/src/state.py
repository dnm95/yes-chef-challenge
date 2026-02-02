import json
import os
from .models import JobState, LineItem

# Path to the persistent storage file
STATE_FILE = os.path.join("data", "job_state.json")

class StateManager:
  """
  Handles durability and recovery.
  Ensures that if the process crashes, we can resume from the exact last saved batch.
  """
  
  def __init__(self):
    self.state = JobState()
    self.load_state()

  def load_state(self):
    """Attempts to load an existing job state from disk."""
    if os.path.exists(STATE_FILE):
      try:
        with open(STATE_FILE, 'r') as f:
          data = json.load(f)
          self.state = JobState(**data)
          print(f"🔄 State Resumed: {self.state.processed_count} items previously processed.")
      except Exception as e:
        print(f"⚠️ Warning: Corrupted state file found. Starting fresh. Error: {e}")

  def save_state(self):
    """Persists the current state to disk."""
    try:
      with open(STATE_FILE, 'w') as f:
        f.write(self.state.model_dump_json(indent=2))
    except Exception as e:
        print(f"❌ Critical Error: Failed to save state. {e}")

  def update_batch(self, new_items: list[LineItem], new_learnings: str):
    """Atomic update of the state after a batch completes."""
    self.state.processed_items.extend(new_items)
    self.state.processed_count += len(new_items)
    # Append new learnings to keep a running log (or replace if strategy changes)
    self.state.current_learnings = f"{self.state.current_learnings} | {new_learnings}"
    self.save_state()

  def get_processed_names(self):
    """Returns a set of item names that are already completed."""
    return {item.item_name for item in self.state.processed_items}
  
  def clear_state(self):
    """Resets the job state (used when user forces a restart)."""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    self.state = JobState()
