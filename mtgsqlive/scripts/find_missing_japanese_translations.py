import json
import csv
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime

def build_japanese_translations_dict(mtgjson_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Build a dictionary of card names to their Japanese translations and text.
    
    Args:
        mtgjson_data: The MTGJSON data dictionary
        
    Returns:
        Dictionary mapping English card names to a dict containing Japanese name, type, text, and flavorText
    """
    translations = {}
    
    for set_data in mtgjson_data["data"].values():
        for card in set_data.get("cards", []):
            if "foreignData" in card:
                for foreign_data in card["foreignData"]:
                    if foreign_data.get("language") == "Japanese":
                        # Store both the original name and the Japanese translation with text and type
                        translations[card["name"]] = {
                            "name": foreign_data.get("name", ""),
                            "type": foreign_data.get("type", ""),
                            "text": foreign_data.get("text", ""),
                            "flavorText": foreign_data.get("flavorText", "")
                        }
    
    return translations

def find_cards_without_japanese_translations(
    mtgjson_data: Dict[str, Any],
    known_translations: Dict[str, Dict[str, str]]
) -> Tuple[List[Tuple[str, str, str, str, str, str, str, str]], List[Tuple[str, str, str]]]:
    """
    Find all cards that don't have Japanese translations.
    
    Args:
        mtgjson_data: The MTGJSON data dictionary
        known_translations: Dictionary of known Japanese translations
        
    Returns:
        Tuple containing:
        - List of tuples (set_code, card_number, english_name, found_translation, found_type, found_text, found_flavor_text, uuid) for cards with found translations
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
                        found_translation["name"],
                        found_translation["type"],
                        found_translation["text"],
                        found_translation["flavorText"],
                        card.get("uuid", "N/A")  # Add UUID for SQL inserts
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

def generate_sql_inserts(found_translations: List[Tuple[str, str, str, str, str, str, str, str]], output_file: Path, batch_size: int = 1000) -> None:
    """
    Generate SQL INSERT statements for found translations using safe batch inserts.
    
    Args:
        found_translations: List of tuples containing translation data
        output_file: Path to write the SQL file
        batch_size: Number of values to include in each batch insert
    """
    with open(output_file, "w", encoding="utf-8") as f:
        # Write header and explanation
        f.write("-- Generated SQL inserts for missing Japanese translations\n")
        f.write(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- IMPORTANT: This script uses INSERT IGNORE to prevent duplicates\n")
        f.write("-- It will NOT overwrite existing Japanese translations\n\n")
        f.write("START TRANSACTION;\n\n")
        
        # Process translations in batches
        for i in range(0, len(found_translations), batch_size):
            batch = found_translations[i:i + batch_size]
            
            # Write individual INSERT statements with existence check
            # This prevents duplicates by checking if the record already exists
            for _, _, _, translation, type_line, text, flavor_text, uuid in batch:
                escaped_translation = translation.replace("\\", "\\\\").replace("'", "''") if translation else ""
                escaped_text = text.replace("\\", "\\\\").replace("'", "''") if text else ""
                escaped_type = type_line.replace("\\", "\\\\").replace("'", "''") if type_line else ""
                escaped_flavor = flavor_text.replace("\\", "\\\\").replace("'", "''") if flavor_text else ""
                
                sql = f"""INSERT INTO cardForeignData (uuid, language, name, type, text, flavorText)
SELECT '{uuid}', 'Japanese', '{escaped_translation}', '{escaped_type}', '{escaped_text}', '{escaped_flavor}'
WHERE NOT EXISTS (
    SELECT 1 FROM cardForeignData 
    WHERE uuid = '{uuid}' AND language = 'Japanese'
);
"""
                f.write(sql)
        
        f.write("COMMIT;\n\n")
        
        # Add a verification query
        f.write("-- Verification query to check inserted records\n")
        f.write("-- SELECT COUNT(*) as japanese_translations_count FROM cardForeignData WHERE language = 'Japanese';\n")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find missing Japanese translations in MTGJSON data")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="AllPrintings.json",
        help="Path to AllPrintings.json file",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output",
        help="Directory to write output files",
    )
    parser.add_argument(
        "--after-date",
        type=str,
        help="Only include sets released after this date (format: YYYY-MM-DD)",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Load MTGJSON data
    with open(args.input, "r", encoding="utf-8") as f:
        mtgjson_data = json.load(f)
    
    # Filter by date if specified
    if args.after_date:
        for set_key in list(mtgjson_data["data"].keys()):
            set_data = mtgjson_data["data"][set_key]
            release_date = set_data.get("releaseDate", "")
            if release_date <= args.after_date:
                del mtgjson_data["data"][set_key]
    
    # Build dictionary of known Japanese translations
    known_translations = build_japanese_translations_dict(mtgjson_data)
    print(f"Found {len(known_translations)} known Japanese translations")
    
    # Find cards without Japanese translations
    found_translations, missing_translations = find_cards_without_japanese_translations(
        mtgjson_data, known_translations
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Write found translations to CSV
    found_file = output_dir / "found_japanese_translations.csv"
    write_csv(
        found_file,
        ["Set Code", "Card Number", "English Name", "Found Translation", "Found Type", "Found Text", "Found Flavor Text"],
        [(set_code, number, name, translation, type_line, text, flavor_text) 
         for set_code, number, name, translation, type_line, text, flavor_text, _ in found_translations]
    )
    
    # Write missing translations to CSV
    missing_file = output_dir / "missing_japanese_translations.csv"
    write_csv(
        missing_file,
        ["Set Code", "Card Number", "English Name"],
        missing_translations
    )
    
    # Generate SQL inserts
    sql_file = output_dir / "insert_japanese_translations.sql"
    generate_sql_inserts(found_translations, sql_file)
    
    print(f"Found {len(found_translations)} cards with translations available from other sets")
    print(f"Found {len(missing_translations)} cards without any Japanese translation")
    print(f"Results written to:")
    print(f"- {found_file}")
    print(f"- {missing_file}")
    print(f"- {sql_file}")

if __name__ == "__main__":
    main() 