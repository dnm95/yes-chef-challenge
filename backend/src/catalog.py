import pandas as pd
from rapidfuzz import process, fuzz, utils

class SyscoCatalog:
  """
  In-memory Search Engine for the Sysco Catalog.
  
  Why RapidFuzz + Pandas?
  - Pandas provides high-performance vectorized data loading and cleaning (ETL).
  - RapidFuzz is a C++ optimized library that is significantly faster (x10-x50) 
    than standard Python 'fuzzywuzzy' or Levenshtein implementations.
  
  For a dataset of ~600 items, this in-memory approach offers sub-millisecond 
  latency without the overhead of managing an external Vector DB (like Pinecone).
  """

  def __init__(self, csv_path: str):
    # --- ETL PIPELINE (Extract, Transform, Load) ---
    # We perform all heavy data cleaning ONCE during server startup.
    # This ensures that search queries are fast (O(1) access) and don't need real-time cleaning.
    
    # 1. LOAD
    self.df = pd.read_csv(csv_path)
    
    # 2. TRANSFORM: Normalize Descriptions
    # Convert to Uppercase to ensure case-insensitive matching later.
    self.df['Product Description'] = self.df['Product Description'].astype(str).str.upper()
    
    # 3. TRANSFORM: Sanitize Currency Data
    # The raw CSV contains strings like "$1,200.50". 
    # We must strip symbols to enable mathematical operations.
    if 'Cost' in self.df.columns:
      self.df['Cost'] = (
        self.df['Cost']
        .astype(str)
        .str.replace('$', '', regex=False) # Remove currency symbol
        .str.replace(',', '', regex=False) # Remove thousands separator
      )
      # Convert to numeric float. 'coerce' turns invalid parsing errors into NaN.
      # fillna(0.0) ensures we never break the math logic downstream.
      self.df['Cost'] = pd.to_numeric(self.df['Cost'], errors='coerce').fillna(0.0)
    
    # 4. INDEXING
    # Convert the column to a python list for RapidFuzz ingestion.
    self.descriptions = self.df['Product Description'].tolist()
    
    print(f"✅ Sysco Catalog Loaded: {len(self.df)} items indexed.")

  def search(self, query: str, limit: int = 5, score_cutoff: int = 50) -> list:
    """
    Performs a semantic-like fuzzy search on the catalog.
    
    Args:
      query: The ingredient name to look for (e.g. "heavy cream").
      limit: Max results to return.
      score_cutoff: Minimum score (0-100) to consider a match. 
        Set to 50 to allow partial matches (finding 'Butter' within 'SALTED BUTTER').
    """
    if not query:
      return []

    # Preprocess query: Apply same normalization (Uppercase) as the catalog
    clean_query = utils.default_process(query).upper()

    # --- ALGORITHM CHOICE: partial_token_sort_ratio ---
    # We chose this specific scorer to solve two edge cases:
    # 1. Substring Matching ('Partial'): 
    #    Query "Milk" should match "WHOLE MILK GALLON" (Score 100).
    #    Standard 'ratio' would give a low score due to length difference.
    # 2. Word Order Independence ('Token Sort'):
    #    Query "Applewood Bacon" should match "BACON APPLEWOOD SMOKED".
    results = process.extract(
      clean_query,
      self.descriptions,
      scorer=fuzz.partial_token_sort_ratio,
      limit=limit,
      score_cutoff=score_cutoff
    )

    formatted_results = []
    
    # Map the search indices back to the full Pandas DataFrame rows
    for desc, score, index in results:
      row = self.df.iloc[index]
      formatted_results.append({
        "sysco_id": str(row['Sysco Item Number']),
        "desc": row['Product Description'],
        "brand": row['Brand'],
        "pack_size": row['Unit of Measure'],
        "case_price": float(row['Cost']), # Safe to cast to float due to __init__ cleaning
        "match_score": round(score, 2)
      })

    return formatted_results
