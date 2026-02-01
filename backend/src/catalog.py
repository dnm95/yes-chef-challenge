import pandas as pd
from rapidfuzz import process, fuzz
import os
from typing import List, Dict, Any

class SyscoCatalog:
    """
    Handles fuzzy searching against the Sysco CSV catalog.
    
    Why RapidFuzz? 
    Standard SQL/String matching fails on 'Applewood Bacon' vs 'BACON, APPLEWOOD, SMOKED'.
    Fuzzy matching allows us to find semantically similar items with high accuracy.
    """

    def __init__(self, csv_path: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Catalog not found at: {csv_path}")
            
        # Load CSV. We force dtype=str to prevent pandas from inferring types incorrectly.
        # We fill NA values to avoid runtime errors during string concatenation.
        self.df = pd.read_csv(csv_path, dtype=str).fillna("")
        
        # Optimization: Pre-compute a 'search_text' column combining Description and Brand
        # This increases the surface area for the fuzzy matcher.
        self.df['search_text'] = self.df['Product Description'] + " " + self.df['Brand']
        
        # Convert to list of dicts for O(1) access by index after search
        self.products = self.df.to_dict('records')
        self.search_keys = self.df['search_text'].tolist()
        
        print(f"✅ Sysco Catalog Loaded: {len(self.products)} items indexed.")

    def search(self, query: str, limit: int = 3, threshold: int = 60) -> List[Dict[str, Any]]:
        """
        Performs a fuzzy search query.
        
        Args:
            query: The ingredient name to look for.
            limit: Max results to return.
            threshold: Minimum score (0-100) to consider a match valid.
        """
        # WRatio handles partial matches better than simple Ratio
        results = process.extract(
            query, 
            self.search_keys, 
            scorer=fuzz.WRatio, 
            limit=limit
        )
        
        matches = []
        for match_tuple in results:
            text, score, idx = match_tuple
            
            if score >= threshold:
                item = self.products[idx]
                
                # Robust Price Parsing: Remove '$' and handle formatting
                try:
                    price_str = str(item.get('Cost', '0')).replace('$', '').replace(',', '')
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                matches.append({
                    "sysco_id": item.get('Sysco Item Number'),
                    "desc": item.get('Product Description'),
                    "pack": item.get('Unit of Measure'),
                    "price_case": price,
                    "match_score": score
                })
                
        return matches
