import sys
import os
import pytest

# Add parent directory to path so we can import 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.catalog import SyscoCatalog

def test_fuzzy_search_logic():
    """
    Verifies that the fuzzy search logic correctly identifies ingredients
    despite naming discrepancies (e.g., 'Applewood Bacon' vs 'BACON, APPLEWOOD').
    """
    catalog_path = os.path.join("data", "sysco_catalog.csv")
    
    # Skip test if file is missing (e.g., in CI environment without data)
    if not os.path.exists(catalog_path):
        pytest.skip("sysco_catalog.csv not found, skipping integration test.")

    catalog = SyscoCatalog(catalog_path)
    
    # Test Case 1: Complex matching
    query = "Applewood smoked bacon"
    results = catalog.search(query)
    
    assert len(results) > 0, "Should find at least one match for bacon"
    top_match = results[0]
    
    # Assertions
    assert top_match['match_score'] > 60, "Match score should be reasonably high"
    assert "BACON" in top_match['desc'], "Result should contain 'BACON'"

def test_search_not_found():
    """
    Verifies that non-existent items return empty lists or low scores,
    rather than hallucinations.
    """
    catalog_path = os.path.join("data", "sysco_catalog.csv")
    if not os.path.exists(catalog_path): return

    catalog = SyscoCatalog(catalog_path)
    
    # Test Case 2: Impossible item
    results = catalog.search("Kryptonite Seasoning")
    
    # Since we filter score > 60 in the class, this should return empty
    assert len(results) == 0, "Should return no results for nonsense query"
