import asyncio
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv

# Internal Modules
from src.catalog import SyscoCatalog
from src.agent import ChefAgent
from src.state import StateManager

# Load environment variables
load_dotenv()

app = FastAPI(title="Yes Chef API", version="1.0.0")

# CORS Configuration: Allows the Next.js frontend to communicate with this API
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- Singleton Initialization ---
# We initialize these once to keep the catalog in memory for performance.
CATALOG_PATH = os.path.join("data", "sysco_catalog.csv")
catalog = SyscoCatalog(CATALOG_PATH)
agent = ChefAgent(catalog)
state_manager = StateManager()

class MenuRequest(BaseModel):
  items: List[Dict[str, Any]]
  reset: bool = False

async def process_menu_background(items: List[Dict[str, Any]]):
  """
  Background Task: Processes the menu in batches.
  Handles robustness, state saving, and context compaction.
  """
  BATCH_SIZE = 3 
  
  # Filter out items that are already done (Resumability Pattern)
  done_names = state_manager.get_processed_names()
  todo_items = [i for i in items if i['name'] not in done_names]
  
  print(f"🚀 Job Started. Total: {len(items)} | Completed: {len(done_names)} | Remaining: {len(todo_items)}")
  state_manager.state.status = "in_progress"
  state_manager.save_state()

  # Process Loop
  while todo_items:
    # Slice the batch
    batch = todo_items[:BATCH_SIZE]
    todo_items = todo_items[BATCH_SIZE:]
    
    current_context = state_manager.state.current_learnings
    print(f"⚡ Processing batch of {len(batch)} items...")
    
    # Async Concurrent Processing: Run all items in batch simultaneously
    tasks = [agent.estimate_item(item, current_context) for item in batch]
    results = await asyncio.gather(*tasks)
    
    # Context Compaction: Learn from this batch
    new_learnings = await agent.compact_context(results)
    print(f"🧠 Learned: {new_learnings}")
    
    # Persist State
    state_manager.update_batch(results, new_learnings)
    print("💾 State Saved.")
      
  state_manager.state.status = "completed"
  state_manager.save_state()
  print("✅ Job Finished Successfully.")

@app.post("/api/estimate")
async def start_estimation(request: MenuRequest, background_tasks: BackgroundTasks):
  """
  Starts the estimation process asynchronously.
  Returns immediately so the UI doesn't freeze.
  """
  if request.reset:
    state_manager.clear_state()
      
  # Schedule the heavy lifting to run in the background
  background_tasks.add_task(process_menu_background, request.items)
  
  return {
    "message": "Estimation started in background",
    "status": "in_progress",
    "processed_so_far": state_manager.state.processed_count
  }

@app.get("/api/status")
def get_status():
  """
  Polling endpoint for the Frontend to check progress.
  """
  return {
    "processed_count": state_manager.state.processed_count,
    "total_items_in_state": len(state_manager.state.processed_items),
    "status": state_manager.state.status,
    "learnings": state_manager.state.current_learnings,
    # Return the latest 5 items for visual feedback
    "latest_items": state_manager.state.processed_items[-5:]
  }
