import json
import csv
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
    Generate SQL INSERT statements for found translations using batch inserts.
    
    Args:
        found_translations: List of tuples containing translation data
        output_file: Path to write the SQL file
        batch_size: Number of values to include in each batch insert
    """
    with open(output_file, "w", encoding="utf-8") as f:
        # Write header
        f.write("-- Generated SQL inserts for missing Japanese translations\n")
        f.write(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("START TRANSACTION;\n\n")
        
        # Process translations in batches
        for i in range(0, len(found_translations), batch_size):
            batch = found_translations[i:i + batch_size]
            
            # Create the VALUES part of the INSERT statement
            values = []
            for _, _, _, translation, type_line, text, flavor_text, uuid in batch:
                # Escape single quotes in text and type
                escaped_text = text.replace("'", "''") if text else ""
                escaped_type = type_line.replace("'", "''") if type_line else ""
                escaped_flavor = flavor_text.replace("'", "''") if flavor_text else ""
                values.append(f"('{uuid}', 'Japanese', '{translation}', '{escaped_type}', '{escaped_text}', '{escaped_flavor}')")
            
            # Write the batch insert statement
            sql = "INSERT INTO cardForeignData (uuid, language, name, type, text, flavorText)\n"
            sql += "VALUES\n"
            sql += ",\n".join(values) + "\n"
            sql += "ON DUPLICATE KEY UPDATE\n"
            sql += "  name = VALUES(name),\n"
            sql += "  type = VALUES(type),\n"
            sql += "  text = VALUES(text),\n"
            sql += "  flavorText = VALUES(flavorText);\n\n"
            f.write(sql)
        
        f.write("COMMIT;\n")

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