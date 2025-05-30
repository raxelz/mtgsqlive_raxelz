import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set

def build_japanese_translations_dict(mtgjson_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Build a dictionary of card names to their Japanese translations.
    
    Args:
        mtgjson_data: The MTGJSON data dictionary
        
    Returns:
        Dictionary mapping English card names to their Japanese translations
    """
    translations = {}
    
    for set_data in mtgjson_data["data"].values():
        for card in set_data.get("cards", []):
            if "foreignData" in card:
                for foreign_data in card["foreignData"]:
                    if foreign_data.get("language") == "Japanese" and "name" in foreign_data:
                        # Store both the original name and the Japanese translation
                        translations[card["name"]] = foreign_data["name"]
    
    return translations

def find_cards_without_japanese_translations(
    mtgjson_data: Dict[str, Any],
    known_translations: Dict[str, str]
) -> Tuple[List[Tuple[str, str, str, str]], List[Tuple[str, str, str]]]:
    """
    Find all cards that don't have Japanese translations.
    
    Args:
        mtgjson_data: The MTGJSON data dictionary
        known_translations: Dictionary of known Japanese translations
        
    Returns:
        Tuple containing:
        - List of tuples (set_code, card_number, english_name, found_translation) for cards with found translations
        - List of tuples (set_code, card_number, english_name) for cards without any translation
    """
    found_translations = []
    missing_translations = []
    
    for set_code, set_data in mtgjson_data["data"].items():
        for card in set_data.get("cards", []):
            has_japanese = False
            
            # Check if card has foreignData
            if "foreignData" in card:
                for foreign_data in card["foreignData"]:
                    if foreign_data.get("language") == "Japanese":
                        has_japanese = True
                        break
            
            if not has_japanese:
                # Try to find translation from other sets
                found_translation = known_translations.get(card["name"])
                if found_translation:
                    found_translations.append((
                        set_code,
                        card.get("number", "N/A"),
                        card.get("name", "N/A"),
                        found_translation
                    ))
                else:
                    missing_translations.append((
                        set_code,
                        card.get("number", "N/A"),
                        card.get("name", "N/A")
                    ))
    
    return found_translations, missing_translations

def write_csv(filename: Path, headers: List[str], rows: List[Tuple]) -> None:
    """Write data to a CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def main():
    # Load MTGJSON data
    with open("AllPrintings.json", "r", encoding="utf-8") as f:
        mtgjson_data = json.load(f)
    
    # Build dictionary of known Japanese translations
    known_translations = build_japanese_translations_dict(mtgjson_data)
    print(f"Found {len(known_translations)} known Japanese translations")
    
    # Find cards without Japanese translations
    found_translations, missing_translations = find_cards_without_japanese_translations(
        mtgjson_data, known_translations
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Write found translations to CSV
    found_file = output_dir / "found_japanese_translations.csv"
    write_csv(
        found_file,
        ["Set Code", "Card Number", "English Name", "Found Translation"],
        found_translations
    )
    
    # Write missing translations to CSV
    missing_file = output_dir / "missing_japanese_translations.csv"
    write_csv(
        missing_file,
        ["Set Code", "Card Number", "English Name"],
        missing_translations
    )
    
    print(f"Found {len(found_translations)} cards with translations available from other sets")
    print(f"Found {len(missing_translations)} cards without any Japanese translation")
    print(f"Results written to:")
    print(f"- {found_file}")
    print(f"- {missing_file}")

if __name__ == "__main__":
    main() 