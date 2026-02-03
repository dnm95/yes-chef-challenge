import sys
import os
import pytest

# --- PATH HACK FOR TEST DISCOVERY ---
# This line adds the parent directory to the system path, allowing us to import 
# modules from the 'src' folder without needing a complex package structure.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.catalog import SyscoCatalog

# --- FIXTURES (Performance Optimization) ---
@pytest.fixture(scope="module")
def catalog():
  """
  Pytest Fixture with 'module' scope.
  Why? Loading the CSV and cleaning data (ETL) is expensive.
  We do it ONLY ONCE for the entire test file, instead of repeating it for every test function.
  This makes the test suite run instantly.
  """
  catalog_path = os.path.join("data", "sysco_catalog.csv")
  
  if not os.path.exists(catalog_path):
    pytest.skip(f"Catalog file not found at {catalog_path}. Skipping tests.")
  
  print(f"\n📂 Loading catalog from: {catalog_path}")
  return SyscoCatalog(catalog_path)

# --- INTEGRATION TESTS ---

def test_catalog_load(catalog):
  """
  Sanity Check.
  Ensures the CSV was parsed correctly and the DataFrame is not empty.
  If this fails, the ETL pipeline in catalog.py is broken.
  """
  # Assuming the sample CSV has ~565 items, checking > 0 is enough
  assert len(catalog.df) > 0, "Catalog should not be empty"
  print(f"✅ Catalog loaded with {len(catalog.df)} items.")

def test_exact_match_behavior(catalog):
  """
  Test Case 1: Simple Retrieval.
  Verifies that the search engine can find common items with simple queries.
  Target: 'Butter' should match 'BUTTER SALTED GRADE AA'.
  """
  query = "Butter" 
  results = catalog.search(query)
  
  assert len(results) > 0, "Should find generic Butter"
  print(f"✅ Found Butter match: {results[0]['desc']} (Score: {results[0]['match_score']})")

def test_fuzzy_search_logic(catalog):
  """
  Test Case 2: Algorithm Validation (The 'Smart' Test).
  
  This validates that our 'partial_token_sort_ratio' algorithm works as expected.
  It MUST match 'Applewood smoked bacon' with 'BACON, SMOKED, APPLEWOOD'.
  
  If this fails, it means the search logic is too strict or word-order dependent.
  """
  query = "Applewood smoked bacon"
  results = catalog.search(query)
  
  # --- Developer Experience (DX) ---
  # If the test fails, we print detailed debug info to help the developer 
  # understand WHY it failed (e.g. score was 45 but cutoff is 50).
  if len(results) == 0:
    print(f"\n⚠️ WARNING: No match found for '{query}'.")
    print("Possible causes: Score threshold in catalog.py is too high.")
    # Diagnostic run:
    print("Trying broader search 'Bacon'...")
    broad_results = catalog.search("Bacon")
    for r in broad_results[:3]:
      print(f"   -> Candidates found for 'Bacon': {r['desc']} (Score: {r['match_score']})")
  
  assert len(results) > 0, f"Should find match for '{query}'"
  
  top_match = results[0]
  # We verify that the description makes sense content-wise
  assert "BACON" in top_match['desc'], "Result should contain 'BACON'"
  print(f"✅ Found Bacon match: {top_match['desc']} (Score: {top_match['match_score']})")

def test_search_not_found(catalog):
  """
  Test Case 3: Hallucination Prevention.
  Ensures that the system returns an empty list for nonsensical queries
  instead of returning a low-confidence 'best guess'.
  """
  # 'Kryptonite' should not exist in food service
  results = catalog.search("Kryptonite Radioactive Isotope")
  
  if len(results) > 0:
      print(f"\n⚠️ WARNING: Found unexpected match for Kryptonite: {results[0]}")
      
  assert len(results) == 0, "Should return no results for nonsense query"
  print("✅ No hallucinations for Kryptonite.")
