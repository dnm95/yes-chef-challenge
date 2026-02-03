import pandas as pd
from rapidfuzz import process, fuzz, utils

class SyscoCatalog:
  def __init__(self, csv_path: str):
    # Load the CSV
    self.df = pd.read_csv(csv_path)
    
    # 1. Preprocess Descriptions: Uppercase for consistency
    self.df['Product Description'] = self.df['Product Description'].astype(str).str.upper()
    
    # This handles strings like "$198.60" or "$1,200.00"
    if 'Cost' in self.df.columns:
        self.df['Cost'] = (
          self.df['Cost']
          .astype(str)
          .str.replace('$', '', regex=False)
          .str.replace(',', '', regex=False)
        )
        # Convert to numeric, turning errors into 0.0
        self.df['Cost'] = pd.to_numeric(self.df['Cost'], errors='coerce').fillna(0.0)
    
    # Create a list of descriptions for RapidFuzz
    self.descriptions = self.df['Product Description'].tolist()
    
    print(f"✅ Sysco Catalog Loaded: {len(self.df)} items indexed.")

  def search(self, query: str, limit: int = 5, score_cutoff: int = 50) -> list:
    """
    Performs a fuzzy search on the catalog.
    
    Args:
      query: The ingredient name to look for (e.g. "heavy cream").
      limit: Max results to return.
      score_cutoff: Minimum score (0-100) to consider a match. 
                    LOWERED TO 50 to catch partial matches like "Butter" inside "BUTTER SALTED".
    """
    if not query:
      return []

    # Preprocess query: Uppercase to match catalog format
    clean_query = utils.default_process(query).upper()

    # --- ALGORITHM CHOICE IS KEY HERE ---
    # fuzz.partial_token_sort_ratio is the best for this use case.
    # 1. 'partial': It matches "Butter" inside "BUTTER SALTED GRADE AA" perfectly (Score 100).
    # 2. 'token_sort': It handles "Applewood Bacon" matching "BACON APPLEWOOD" (Score 100).
    results = process.extract(
      clean_query,
      self.descriptions,
      scorer=fuzz.partial_token_sort_ratio,
      limit=limit,
      score_cutoff=score_cutoff
    )

    formatted_results = []
    
    for desc, score, index in results:
      row = self.df.iloc[index]
      formatted_results.append({
        "sysco_id": str(row['Sysco Item Number']),
        "desc": row['Product Description'],
        "brand": row['Brand'],
        "pack_size": row['Unit of Measure'],
        "case_price": float(row['Cost']), # Now safe to convert
        "match_score": round(score, 2)
      })

    return formatted_results
