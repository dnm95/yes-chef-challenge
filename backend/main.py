import asyncio
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Internal modules import
from src.catalog import SyscoCatalog
from src.agent import ChefAgent
from src.state import StateManager

# Load environment variables (API Keys) from .env file
load_dotenv()

# Initialize the API application
app = FastAPI(title="Yes Chef API", version="1.0.0")

# --- CORS CONFIGURATION ---
# Vital for allowing the Next.js Frontend (running on a different port/domain)
# to communicate with this Backend.
app.add_middleware(
  CORSMiddleware,
  # Allow both localhost (dev) and Vercel (prod)
  allow_origins=["http://localhost:3000", "https://yes-chef-challenge.vercel.app"],
  allow_credentials=True,
  allow_methods=["*"], # Allow all HTTP methods (GET, POST, etc.)
  allow_headers=["*"],
)

# --- SINGLETON INITIALIZATION ---
# We load heavy resources (Catalog, Agent, State) only ONCE when the server starts.
# This prevents reloading the CSV or reconnecting to OpenAI on every single request.
CATALOG_PATH = os.path.join("data", "sysco_catalog.csv")
catalog = SyscoCatalog(CATALOG_PATH)
agent = ChefAgent(catalog)
state_manager = StateManager()

# --- REQUEST MODELS (Pydantic) ---
# Pydantic enforces strict type validation. If the frontend sends bad data,
# these models will auto-generate a 422 Error before reaching our logic.

class MenuRequest(BaseModel):
  items: List[Dict[str, Any]] # List of menu items to process
  reset: bool = False # Flag to clear previous job state

class TextEstimationRequest(BaseModel):
  text: str # Raw natural language from chat
  reset: bool = True

# --- CORE LOGIC: BACKGROUND WORKER ---
async def process_menu_background(items: List[Dict[str, Any]]):
  """
  The Orchestrator Logic.
  It handles Batching, Context Compaction, and State Persistence.
  Run as a background task to avoid blocking the HTTP response.
  """
  BATCH_SIZE = 3 # Process 3 items at a time to manage LLM context window
  
  # --- 1. RESUMABILITY CHECK ---
  # Before starting, check the persistent state (JSON) to see what's already done.
  # This ensures that if the server crashes, we skip already processed items.
  done_names = state_manager.get_processed_names()
  todo_items = [i for i in items if i['name'] not in done_names]
  
  print(f"🚀 Job Started. Total: {len(items)} | Remaining: {len(todo_items)}")
  
  # Update status to 'in_progress' so the frontend shows the loading bar
  state_manager.state.status = "in_progress"
  state_manager.save_state()

  # --- 2. BATCH PROCESSING LOOP ---
  while todo_items:
    # Slice the list to get the next N items
    batch = todo_items[:BATCH_SIZE]
    todo_items = todo_items[BATCH_SIZE:]
    
    # Retrieve 'Learnings' from the previous batch (Context Compaction)
    current_learnings = state_manager.state.current_learnings
    print(f"⚡ Processing batch of {len(batch)}...")
    
    # --- 3. CONCURRENCY (Async/Await) ---
    # We create a list of tasks and run them in parallel using asyncio.gather.
    # This is much faster than processing items one by one sequentially.
    tasks = [agent.estimate_item(item, current_learnings) for item in batch]
    results = await asyncio.gather(*tasks)
    
    # --- 4. LEARN & UPDATE ---
    # Summarize new insights (e.g., "Sysco lacks Wagyu") to carry forward.
    new_learnings = await agent.compact_context(results)
    print(f"🧠 New Insights: {new_learnings}")
    
    # Atomic State Update: Save results and learnings to disk immediately.
    state_manager.update_batch(results, new_learnings)
      
  # Mark job as complete
  state_manager.state.status = "completed"
  state_manager.save_state()
  print("✅ Job Finished.")

# --- API ENDPOINTS ---

@app.post("/api/estimate")
async def start_estimation_json(request: MenuRequest, background_tasks: BackgroundTasks):
  """
  Endpoint for JSON Mode.
  Receives a structured list of items and offloads processing to the background.
  """
  if request.reset:
    state_manager.clear_state()
  
  # Trigger the worker without making the user wait for completion
  background_tasks.add_task(process_menu_background, request.items)
  
  # Return immediately with "in_progress" status
  return {"status": "in_progress", "mode": "json_direct"}

@app.post("/api/estimate-text")
async def start_estimation_text(request: TextEstimationRequest, background_tasks: BackgroundTasks):
  """
  Endpoint for Chat Mode (NLP Pipeline).
  1. Receives raw text.
  2. Uses AI to Parse text -> JSON.
  3. Starts the standard background estimation.
  """
  if request.reset:
    state_manager.clear_state()

  print(f"🗣️  Received Natural Language Request: {request.text[:50]}...")
  
  try:
    # Step 1: Parse Text (Await because it's an external API call to OpenAI)
    structured_data = await agent.parse_menu_request(request.text)
    items = structured_data.get("items", [])
    
    if not items:
      raise HTTPException(status_code=400, detail="Could not identify menu items in text.")

    # Step 2: Hand off to the same background worker used by JSON mode
    print(f"✅ Parsed {len(items)} items from text. Starting estimation...")
    background_tasks.add_task(process_menu_background, items)
    
    return {"status": "in_progress", "mode": "text_parsed", "parsed_count": len(items)}
      
  except Exception as e:
    print(f"❌ Error parsing text: {e}")
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
def get_status():
  """
  Polling Endpoint.
  The Frontend calls this every 2 seconds to check progress and update the UI.
  Reads directly from the StateManager (in-memory/disk).
  """
  return {
    "processed_count": state_manager.state.processed_count,
    "total_items_in_state": len(state_manager.state.processed_items),
    "status": state_manager.state.status,
    "learnings": state_manager.state.current_learnings,
    # Return ALL items so the frontend shows the full history growing
    "latest_items": state_manager.state.processed_items
  }
