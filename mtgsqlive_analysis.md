# MTGSQLive Project Architecture Analysis

## Executive Summary

The MTGSQLive project is an ETL (Extract, Transform, Load) tool that converts MTGJSON data files (primarily `AllPrintings.json` and `AllPricesToday.json`) into multiple output formats including MySQL, PostgreSQL, SQLite, CSV, and Parquet. The architecture uses a converter pattern with a base class hierarchy supporting different output formats.

---

## 1. JSON File Processing Pipeline

### 1.1 Entry Point and File Loading

**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/__main__.py`

**Key Function**: `main()` (lines 108-169)

**Processing Flow**:

```
1. Parse command-line arguments (lines 111)
2. Determine input type - file or directory (lines 122-142)
3. For each data type to process:
   - Load JSON file into memory (lines 150-151)
   - Apply filtering: specific sets (lines 153-156)
   - Apply filtering: by release date (lines 158-163)
   - Pass to converters (lines 165-168)
```

**Critical Code Snippet** (lines 150-151):
```python
with mtgjson_input_file.open(encoding="utf-8") as fp:
    mtgjson_input_data = json.load(fp)
```

**Input Support** (lines 122-142):
- Accepts both file path and directory path
- If file is passed, extracts stem and looks up matching `MtgjsonDataType`
- If directory is passed, processes all available data types

### 1.2 Supported Data Types

**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/enums/data_type.py`

```python
class MtgjsonDataType(enum.Enum):
    MTGJSON_CARDS = "AllPrintings"
    MTGJSON_CARD_PRICES = "AllPricesToday"
```

Currently supports 2 data types. To add support for individual set files (like `SPM.json`):
- Add enum value: `MTGJSON_SPM = "SPM"`
- The framework would automatically handle it

### 1.3 Data Structure Expected

The loaded JSON is expected to have this structure:
```python
{
    "meta": {
        "date": "YYYY-MM-DD",
        "version": "X.X.X"
    },
    "data": {
        "SET_CODE": {
            # Set metadata
            "releaseDate": "YYYY-MM-DD",
            # Arrays
            "cards": [...],
            "tokens": [...],
            "booster": {...},
            "translations": {...},
            # Other set-level fields
        },
        # More sets...
    }
}
```

---

## 2. SQL Generation Logic

### 2.1 Architecture Overview

The SQL generation uses a multi-level class hierarchy:

```
AbstractConverter (abstract base)
    ├── SqlLikeConverter (abstract, provides batch INSERT generation)
    │   ├── MysqlConverter (concrete)
    │   ├── PostgresqlConverter (concrete)
    │   └── SqliteConverter (concrete, outputs .sqlite database)
    └── SqliteBasedConverter (abstract, for CSV/Parquet)
        ├── CsvConverter (concrete)
        └── ParquetConverter (concrete)
```

### 2.2 SQL Generation Entry Points

**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/sql_like.py`

**Key Method**: `generate_database_insert_statements()` (lines 27-37)

**Generator Chain**:
```
1. Determine data type (MTGJSON_CARDS or MTGJSON_CARD_PRICES)
2. Get list of generators:
   - For MTGJSON_CARDS: 14 generators (meta, sets, cards, tokens, etc.)
   - For MTGJSON_CARD_PRICES: 1 generator (cardPrices)
3. Each generator yields SQL INSERT statements
```

**Generators for MTGJSON_CARDS** (lines 40-81):
1. `meta` - Version info
2. `sets` - Set metadata
3. `cards` - Card details
4. `tokens` - Token cards
5. `cardIdentifiers` - Card IDs (normalized)
6. `cardLegalities` - Format legality data
7. `cardRulings` - Rulings data
8. `cardForeignData` - Foreign language data
9. `cardPurchaseUrls` - Purchase URLs
10. `tokenIdentifiers` - Token identifiers
11. `setTranslations` - Set translations
12. `setBoosterContents` - Booster packaging info
13. `setBoosterContentWeights` - Booster weights
14. `setBoosterSheets` - Booster sheet definitions
15. `setBoosterSheetCards` - Cards in booster sheets

### 2.3 Batch INSERT Generation

**Critical Method**: `__generate_batch_insert_statement()` (lines 101-144)

**Features**:
- Batch size: 2,000 rows per INSERT statement (configurable via `self.batch_size`)
- Generates multi-row INSERT statements for efficiency
- Uses database schema to ensure consistent column ordering
- Handles missing values by inserting NULL

**Output Format** (Example):
```sql
INSERT INTO cards (cmc, colorIdentity, colors, convertedManaCost, ...)
VALUES
('0', '["U"]', '["U"]', '0', ...),
('0', '["R"]', '["R"]', '0', ...),
('0', '["W"]', '["W"]', '0', ...);
```

**Processing Steps** (lines 114-144):
1. Get all columns from schema (excluding `id` and `unique_constraint`)
2. Sort columns alphabetically for consistency
3. For each data object:
   - Create complete object with all schema columns
   - Fill missing values with NULL
   - Build value tuple with proper escaping
4. Accumulate 2,000 rows, then flush and output
5. Final batch contains remaining rows

### 2.4 Schema Generation

**Critical Method**: `_generate_sql_schema_dict()` (lines 146-168)

**Schema Structure**:
- Analyzes actual data to determine column types
- Defines tables for each entity type
- Sets up constraints and indexes

**Type Inference** (lines 334-343):
```python
def _get_sql_type(mixed: Any) -> Optional[str]:
    if isinstance(mixed, (str, list, dict)):
        return "TEXT"
    if isinstance(mixed, bool):
        return "BOOLEAN"
    if isinstance(mixed, float):
        return "FLOAT"
    if isinstance(mixed, int):
        return "INTEGER"
```

**Database-Specific Implementations**:

#### MySQL Converter
**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/mysql.py`

- Primary key: `INTEGER PRIMARY KEY AUTO_INCREMENT`
- Engine: `InnoDB DEFAULT CHARSET=utf8mb4`
- Value escaping: Uses `pymysql.converters.escape_string()`
- Output file: `{data_type}.sql` (e.g., `AllPrintings.sql`)

#### PostgreSQL Converter
**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/postgresql.py`

- Primary key: `SERIAL PRIMARY KEY`
- Value escaping: Custom with `'` and `"` handling
- Output file: `{data_type}.psql`

#### SQLite Converter
**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/sqlite.py`

- Creates actual SQLite database file: `{data_type}.sqlite`
- Uses `sqlite3.connect()` and `executescript()`
- Runs schema and inserts directly against database
- Output file: `{data_type}.sqlite` (binary database file)

### 2.5 Data Extraction Methods

**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/abstract.py`

These methods provide generators that iterate through JSON data and normalize it:

| Method | Lines | Purpose |
|--------|-------|---------|
| `get_metadata()` | 51-52 | Extract meta info |
| `get_next_set()` | 57-63 | Iterate sets, skip nested arrays |
| `get_next_card_like()` | 79-86 | Iterate cards/tokens |
| `get_next_card_field_with_normalization()` | 111-125 | Extract nested card fields (legalities, rulings, etc.) |
| `get_next_card_identifier()` | 88-89 | Extract card identifiers |
| `get_next_card_legalities()` | 91-92 | Extract format legality |
| `get_next_card_ruling_entry()` | 94-97 | Extract rulings |
| `get_next_card_foreign_data_entry()` | 99-102 | Extract foreign language data |
| `get_next_booster_contents_entry()` | 172-183 | Extract booster packaging |

---

## 3. Individual Set JSON File Support (SPM.json)

### 3.1 Current Status

**Location**: SPM.json exists at project root
**Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/SPM.json`

**Current Framework Support**:
- The `__main__.py` already supports individual JSON files (lines 122-142)
- If you pass `SPM.json` directly, it will:
  1. Extract the stem: `SPM`
  2. Look for matching `MtgjsonDataType` enum
  3. Fail if not found in enum

### 3.2 How to Add SPM.json Support

**Step 1**: Add to enum
```python
# File: /Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/enums/data_type.py
class MtgjsonDataType(enum.Enum):
    MTGJSON_CARDS = "AllPrintings"
    MTGJSON_CARD_PRICES = "AllPricesToday"
    MTGJSON_SPM = "SPM"  # Add this
```

**Step 2**: Handle in converter selection
- If SPM.json has same structure as AllPrintings (meta + data.cards), use existing converters
- `SqlLikeConverter.generate_database_insert_statements()` would need adjustment to handle SPM data type
- Currently it only handles `MTGJSON_CARDS` and `MTGJSON_CARD_PRICES` (lines 28-33)

**Step 3**: Conditional processing
```python
# In sql_like.py generate_database_insert_statements()
if self.data_type in (MtgjsonDataType.MTGJSON_CARDS, MtgjsonDataType.MTGJSON_SPM):
    generators = self.__get_mtgjson_card_generators()
elif self.data_type == MtgjsonDataType.MTGJSON_CARD_PRICES:
    generators = self.__get_mtgjson_card_prices_generators()
```

---

## 4. Key Conversion Flow Example

### Example: Processing AllPrintings.json to MySQL SQL

```
1. main() loads AllPrintings.json
   └─> mtgjson_input_data = {"meta": {...}, "data": {"M10": {...}, ...}}

2. Instantiate converters for each enabled format
   └─> MysqlConverter(mtgjson_input_data, output_dir, MtgjsonDataType.MTGJSON_CARDS)

3. MysqlConverter.convert() is called
   ├─> _generate_sql_schema_dict()
   │   ├─> Analyzes mtgjson_data["data"] for all sets
   │   ├─> Iterates cards, tokens, builds schema for each table
   │   └─> Returns: {"sets": {...}, "cards": {...}, ...}
   │
   ├─> _convert_schema_dict_to_query()
   │   └─> Generates CREATE TABLE statements
   │
   ├─> Writes file header with metadata
   │
   ├─> generate_database_insert_statements()
   │   ├─> __get_mtgjson_card_generators() returns 14 generators
   │   └─> Each generator yields normalized data objects
   │
   ├─> For each generator:
   │   └─> __generate_batch_insert_statement()
   │       ├─> Accumulates 2,000 rows
   │       ├─> Calls create_insert_statement_body() for escaping
   │       └─> Yields: "INSERT INTO table (...) VALUES\n(...),\n(...);"
   │
   └─> Writes all statements to AllPrintings.sql

4. Output file contains:
   - Header with metadata
   - CREATE TABLE statements
   - INSERT statements with batches of 2,000 rows
   - COMMIT statements
```

---

## 5. File Processing with Filtering

### 5.1 Filtering by Set Code

**Code**: `__main__.py` lines 153-156
```python
if args.sets:
    for set_key in list(mtgjson_input_data["data"].keys()):
        if set_key not in args.sets:
            del mtgjson_input_data["data"][set_key]
```

**Usage**:
```bash
python -m mtgsqlive -i AllPrintings.json -o output --mysql -s M10 M11 M12
```

### 5.2 Filtering by Release Date

**Code**: `__main__.py` lines 158-163
```python
if args.after_date:
    for set_key in list(mtgjson_input_data["data"].keys()):
        set_data = mtgjson_input_data["data"][set_key]
        release_date = set_data.get("releaseDate", "")
        if release_date <= args.after_date:
            del mtgjson_input_data["data"][set_key]
```

**Usage**:
```bash
python -m mtgsqlive -i AllPrintings.json -o output --mysql --after-date 2024-01-01
```

---

## 6. Data Normalization and Field Skipping

### 6.1 Fields Skipped from Sets

**Code**: `abstract.py` lines 23-30
```python
set_keys_to_skip = {
    "booster",  # Normalized into separate tables
    "cards",    # Normalized into separate tables
    "decks",    # WIP
    "sealedProduct",  # WIP
    "tokens",   # Normalized into separate tables
    "translations",  # Normalized as setTranslations
}
```

These are broken out into separate generators and tables.

### 6.2 Fields Skipped from Cards

**Code**: `abstract.py` lines 31-38
```python
card_keys_to_skip = {
    "convertedManaCost",  # Redundant with manaValue
    "foreignData",  # Separate cardForeignData table
    "identifiers",  # Separate cardIdentifiers table
    "legalities",  # Separate cardLegalities table
    "purchaseUrls",  # Separate cardPurchaseUrls table
    "rulings",  # Separate cardRulings table
}
```

These are normalized into separate tables for 3rd normal form.

---

## 7. Current Project Status

### Branch Information
- **Current Branch**: `feature/switch_sql_to_batch`
- **Main Branch**: `master`
- **Modified Files**:
  - `README.md` - Documentation updates
  - `mtgsqlive/scripts/find_missing_japanese_translations.py` - Japanese translation handling

### Recent Changes
1. **Batch INSERT statements** - Changed from single-row to 2,000 row batches
2. **Date filtering** - Added `--after-date` parameter
3. **File input support** - Can now accept individual JSON files
4. **Japanese translation script** - Added to find and fill missing translations

### Example Script: Japanese Translations
**File**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/scripts/find_missing_japanese_translations.py`

Generates SQL INSERT statements for missing Japanese translations:
```python
sql = f"""INSERT INTO cardForeignData (uuid, language, name, type, text, flavorText)
VALUES ('{uuid}', 'Japanese', '{escaped_name}', '{escaped_type}', '{escaped_text}', '{escaped_flavor_text}')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    type = VALUES(type),
    text = VALUES(text),
    flavorText = VALUES(flavorText);"""
```

---

## 8. Summary Table: Key Files and Responsibilities

| File | Responsibility | Key Methods |
|------|------------------|-------------|
| `__main__.py` | Entry point, arg parsing, JSON loading, filtering | `main()`, `parse_args()` |
| `enums/data_type.py` | Data type definitions | `MtgjsonDataType` enum |
| `converters/parents/abstract.py` | JSON data extraction and normalization | `get_next_*()` methods |
| `converters/parents/sql_like.py` | SQL generation pipeline | `generate_database_insert_statements()`, `__generate_batch_insert_statement()` |
| `converters/mysql.py` | MySQL-specific SQL generation | `create_insert_statement_body()` |
| `converters/postgresql.py` | PostgreSQL-specific SQL generation | `create_insert_statement_body()` |
| `converters/sqlite.py` | SQLite database creation | Database transaction handling |
| `converters/csv.py` | CSV export | Uses SQLite temp database |
| `converters/parquet.py` | Parquet export | Uses pandas/pyarrow |

---

## 9. Architecture Strengths and Design Patterns

1. **Strategy Pattern**: Different converters for different output formats
2. **Template Method Pattern**: Abstract converter defines structure, subclasses implement details
3. **Generator Pattern**: Memory-efficient processing using Python generators
4. **Builder Pattern**: Schema generation and query building
5. **Data Normalization**: Denormalized JSON converted to normalized relational schema
6. **Batch Processing**: 2,000 row batches for performance

