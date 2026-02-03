import sys
import os
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.catalog import SyscoCatalog

@pytest.fixture(scope="module")
def catalog():
  catalog_path = os.path.join("data", "sysco_catalog.csv")
  
  if not os.path.exists(catalog_path):
    pytest.skip(f"Catalog file not found at {catalog_path}. Skipping tests.")
  
  print(f"\n📂 Loading catalog from: {catalog_path}")
  return SyscoCatalog(catalog_path)

def test_catalog_load(catalog):
  """
  Basics: Does the catalog contain items?
  """
  # Assuming the sample CSV has ~565 items, checking > 0 is enough
  assert len(catalog.df) > 0, "Catalog should not be empty"
  print(f"✅ Catalog loaded with {len(catalog.df)} items.")

def test_exact_match_behavior(catalog):
  """
  Test Case 1: Searching for something we KNOW exists (Simple Match).
  Wait... Sysco descriptions are weird. Let's try 'BUTTER'.
  """
  query = "Butter" 
  results = catalog.search(query)
  
  assert len(results) > 0, "Should find generic Butter"
  print(f"✅ Found Butter match: {results[0]['desc']} (Score: {results[0]['match_score']})")

def test_fuzzy_search_logic(catalog):
  """
  Test Case 2: Complex matching (The 'Bacon' test).
  We print the score to debug if it fails.
  """
  query = "Applewood smoked bacon"
  results = catalog.search(query)
  
  # Debug info if results are empty
  if len(results) == 0:
      print(f"\n⚠️ WARNING: No match found for '{query}'.")
      print("Possible causes: Score threshold in catalog.py is too high.")
      # Let's try a broader search to see what's happening
      print("Trying broader search 'Bacon'...")
      broad_results = catalog.search("Bacon")
      for r in broad_results[:3]:
          print(f"   -> Candidates found for 'Bacon': {r['desc']} (Score: {r['match_score']})")
  
  assert len(results) > 0, f"Should find match for '{query}'"
  
  top_match = results[0]
  # We verify that the description makes sense
  assert "BACON" in top_match['desc'], "Result should contain 'BACON'"
  print(f"✅ Found Bacon match: {top_match['desc']} (Score: {top_match['match_score']})")

def test_search_not_found(catalog):
  """
  Test Case 3: Verify we don't hallucinate results for nonsense.
  """
  # 'Kryptonite' should not exist in food service
  results = catalog.search("Kryptonite Radioactive Isotope")
  
  if len(results) > 0:
      print(f"\n⚠️ WARNING: Found unexpected match for Kryptonite: {results[0]}")
      
  assert len(results) == 0, "Should return no results for nonsense query"
  print("✅ No hallucinations for Kryptonite.")
