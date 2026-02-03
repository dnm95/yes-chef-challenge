import asyncio
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.catalog import SyscoCatalog
from src.agent import ChefAgent
from src.state import StateManager

load_dotenv()

app = FastAPI(title="Yes Chef API", version="1.0.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "https://yes-chef-challenge.vercel.app"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- Initialization ---
CATALOG_PATH = os.path.join("data", "sysco_catalog.csv")
catalog = SyscoCatalog(CATALOG_PATH)
agent = ChefAgent(catalog)
state_manager = StateManager()

# --- Request Models ---
class MenuRequest(BaseModel):
  items: List[Dict[str, Any]]
  reset: bool = False

class TextEstimationRequest(BaseModel):
  text: str
  reset: bool = True

# --- Background Worker ---
async def process_menu_background(items: List[Dict[str, Any]]):
  """
  Core Logic: Batch processing with Context Compaction and State Persistence.
  """
  BATCH_SIZE = 3
  
  # Resumability Logic: Filter out completed items
  done_names = state_manager.get_processed_names()
  todo_items = [i for i in items if i['name'] not in done_names]
  
  print(f"🚀 Job Started. Total: {len(items)} | Remaining: {len(todo_items)}")
  state_manager.state.status = "in_progress"
  state_manager.save_state()

  while todo_items:
    batch = todo_items[:BATCH_SIZE]
    todo_items = todo_items[BATCH_SIZE:]
    
    current_learnings = state_manager.state.current_learnings
    print(f"⚡ Processing batch of {len(batch)}...")
    
    tasks = [agent.estimate_item(item, current_learnings) for item in batch]
    results = await asyncio.gather(*tasks)
    
    new_learnings = await agent.compact_context(results)
    print(f"🧠 New Insights: {new_learnings}")
    
    state_manager.update_batch(results, new_learnings)
      
  state_manager.state.status = "completed"
  state_manager.save_state()
  print("✅ Job Finished.")

# --- Endpoints ---

@app.post("/api/estimate")
async def start_estimation_json(request: MenuRequest, background_tasks: BackgroundTasks):
  """
  Mode 1: Direct JSON Input.
  """
  if request.reset:
    state_manager.clear_state()
  
  background_tasks.add_task(process_menu_background, request.items)
  
  return {"status": "in_progress", "mode": "json_direct"}

@app.post("/api/estimate-text")
async def start_estimation_text(request: TextEstimationRequest, background_tasks: BackgroundTasks):
  """
  Mode 2: Natural Language Input.
  Pipeline: Text -> Agent Parsing -> JSON -> Background Estimation.
  """
  if request.reset:
    state_manager.clear_state()

  print(f"🗣️  Received Natural Language Request: {request.text[:50]}...")
  
  try:
    # Step 1: Parse Text to JSON (Await the agent)
    structured_data = await agent.parse_menu_request(request.text)
    items = structured_data.get("items", [])
    
    if not items:
      raise HTTPException(status_code=400, detail="Could not identify menu items in text.")

    # Step 2: Start the Background Job with the parsed items
    print(f"✅ Parsed {len(items)} items from text. Starting estimation...")
    background_tasks.add_task(process_menu_background, items)
    
    return {"status": "in_progress", "mode": "text_parsed", "parsed_count": len(items)}
      
  except Exception as e:
    print(f"❌ Error parsing text: {e}")
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
def get_status():
  return {
    "processed_count": state_manager.state.processed_count,
    "total_items_in_state": len(state_manager.state.processed_items),
    "status": state_manager.state.status,
    "learnings": state_manager.state.current_learnings,
    "latest_items": state_manager.state.processed_items[-5:]
  }
