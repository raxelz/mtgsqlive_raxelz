# MTGSQLive Quick Reference Guide

## File Structure and Key Components

### Core Application Files

#### 1. Entry Point
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/__main__.py`
- **Purpose**: Main CLI entry point
- **Key Functions**:
  - `main()` (lines 108-169): Orchestrates the entire conversion process
  - `parse_args()` (lines 55-105): Parses command-line arguments
  - `get_converters()` (lines 43-52): Returns available converters
- **Critical Code**:
  - JSON loading: line 151 `mtgjson_input_data = json.load(fp)`
  - File vs directory detection: lines 122-142
  - Filtering by sets: lines 153-156
  - Filtering by date: lines 158-163

#### 2. Data Type Definitions
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/enums/data_type.py`
- **Purpose**: Defines supported MTGJSON data types
- **Current Types**:
  - `MTGJSON_CARDS = "AllPrintings"` (line 5)
  - `MTGJSON_CARD_PRICES = "AllPricesToday"` (line 6)

### Converter Architecture

#### Abstract Base Classes

##### AbstractConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/abstract.py`
- **Purpose**: Base class for all converters
- **Key Methods**:
  - `get_metadata()` (lines 51-52): Extract MTGJSON metadata
  - `get_next_set()` (lines 57-63): Iterate through sets, filtering nested arrays
  - `get_next_card_like()` (lines 79-86): Iterate through cards/tokens
  - `get_next_card_field_with_normalization()` (lines 111-125): Extract normalized card fields
  - `get_next_card_identifier()` (line 88-89): Card IDs
  - `get_next_card_legalities()` (line 91-92): Format legality
  - `get_next_card_ruling_entry()` (line 94-97): Card rulings
  - `get_next_card_foreign_data_entry()` (line 99-102): Foreign language data
  - `get_next_booster_contents_entry()` (line 172-183): Booster packaging
  - `get_next_booster_weights_entry()` (line 185-194): Booster weight info
  - `get_next_booster_sheets_entry()` (line 196-208): Booster sheet definitions
  - `get_next_booster_sheet_cards_entry()` (line 210-221): Cards in booster sheets
  - `get_next_card_price()` (line 134-170): Card pricing data

**Field Skipping**:
- Sets: lines 23-30 (booster, cards, decks, sealedProduct, tokens, translations)
- Cards: lines 31-38 (convertedManaCost, foreignData, identifiers, legalities, purchaseUrls, rulings)

##### SqlLikeConverter (SQL-based converters)
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/sql_like.py`
- **Purpose**: Base class for MySQL, PostgreSQL, SQLite converters
- **Key Methods**:
  - `generate_database_insert_statements()` (lines 27-37): Main SQL generation entry point
    - Checks data type and selects appropriate generators
  - `__get_mtgjson_card_generators()` (lines 39-81): Returns list of 14 generators for cards data
  - `__get_mtgjson_card_prices_generators()` (lines 83-91): Returns 1 generator for prices data
  - `__generate_batch_insert_statement()` (lines 101-144): **CRITICAL** - Generates batched INSERT statements
    - Batch size: 2,000 rows (line 17, configurable via `self.batch_size`)
    - Schema-driven column ordering: lines 119-128
    - NULL padding for missing values: line 132
    - Accumulates rows and flushes: lines 136-144
  - `_generate_sql_schema_dict()` (lines 146-168): Builds schema from data
  - `_convert_schema_dict_to_query()` (lines 306-331): Converts schema dict to SQL CREATE TABLE statements
  - `_get_sql_type()` (lines 334-343): Type inference (TEXT, BOOLEAN, FLOAT, INTEGER)

**Table Generators Called** (lines 40-81):
1. meta (line 41)
2. sets (line 42)
3. cards (line 43)
4. tokens (lines 44-45)
5. cardIdentifiers (lines 47-48)
6. cardLegalities (lines 50-51)
7. cardRulings (lines 53-54)
8. cardForeignData (lines 56-57)
9. cardPurchaseUrls (lines 59-60)
10. tokenIdentifiers (lines 62-63)
11. setTranslations (lines 66-67)
12. setBoosterContents (lines 70)
13. setBoosterContentWeights (lines 72-73)
14. setBoosterSheets (lines 75-76)
15. setBoosterSheetCards (lines 78-79)

##### SqliteBasedConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/sqlite_based_converter.py`
- **Purpose**: Base class for CSV and Parquet converters
- **Key Methods**:
  - `get_table_names()` (lines 25-29): Query SQLite for table names
  - `get_table_dataframe()` (lines 31-32): Read table into pandas DataFrame

#### Concrete Converters (SQL Output)

##### MysqlConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/mysql.py`
- **Key Points**:
  - Primary key: `INTEGER PRIMARY KEY AUTO_INCREMENT` (line 49)
  - Engine: `InnoDB DEFAULT CHARSET=utf8mb4` (line 48)
  - Output file: `{data_type}.sql` (lines 31-33)
  - Value escaping: `pymysql.converters.escape_string()` (lines 92-99)
  - `convert()` method (lines 35-72): Orchestrates conversion
  - `create_insert_statement_body()` (lines 74-102): Creates escaped VALUES clause

##### PostgresqlConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/postgresql.py`
- **Key Points**:
  - Primary key: `SERIAL PRIMARY KEY` (line 24)
  - Output file: `{data_type}.psql` (lines 15-17)
  - Value escaping: Custom with `'` and `"` handling (lines 56-67)
  - `create_insert_statement_body()` (lines 47-69): PostgreSQL-specific escaping

##### SqliteConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/sqlite.py`
- **Key Points**:
  - Output: Binary SQLite database file (line 21)
  - Uses `sqlite3.connect()` (lines 20-23)
  - Executes schema and inserts directly: lines 31, 78, 81
  - Batch execution in 1,000 statement batches: line 77

#### Concrete Converters (Other Formats)

##### CsvConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/csv.py`
- **Key Points**:
  - Output directory: `csv/` subdirectory (line 12)
  - Uses `pd.to_csv()` (lines 18-26)
  - One CSV file per table

##### ParquetConverter
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parquet.py`
- **Key Points**:
  - Output directory: `parquet/` subdirectory (line 15)
  - Uses PyArrow: `pyarrow.Table.from_pandas()` (lines 21-23)
  - Writes with `pyarrow.parquet.write_table()` (lines 25-31)
  - One Parquet file per table

### Scripts

#### Japanese Translation Script
- **Path**: `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/scripts/find_missing_japanese_translations.py`
- **Key Functions**:
  - `build_japanese_translations_dict()` (starts line 10): Build translation lookup
  - `find_cards_without_japanese_translations()` (starts line 30): Find missing translations
  - `generate_insert_sql_statements()` (likely): Generate INSERT statements with batch sizes of 1,000
- **Usage**:
  ```bash
  fresh_env/bin/python -m mtgsqlive.scripts.find_missing_japanese_translations
  ```

## Processing Flow Diagram

```
Command Line
    |
    v
parse_args() (__main__.py:55-105)
    |
    v
Determine input type (__main__.py:122-142)
    |
    ├─> File path: Extract stem, lookup MtgjsonDataType enum
    └─> Directory: Process all available data types
    |
    v
Load JSON (__main__.py:150-151)
json.load(fp) -> mtgjson_input_data
    |
    v
Apply Filters (__main__.py:153-163)
    ├─> Filter by sets (--sets flag)
    └─> Filter by date (--after-date flag)
    |
    v
Instantiate Converters (__main__.py:113-117)
    |
    v
For each Converter:
    |
    ├─> convert() method
    |   |
    |   ├─> _generate_sql_schema_dict() (sql_like.py:146-168)
    |   |   |
    |   |   ├─> Analyze mtgjson_data to determine types
    |   |   └─> Build schema dict
    |   |
    |   ├─> _convert_schema_dict_to_query() (sql_like.py:306-331)
    |   |   └─> Generate CREATE TABLE statements
    |   |
    |   └─> generate_database_insert_statements() (sql_like.py:27-37)
    |       |
    |       ├─> __get_mtgjson_card_generators() or
    |       └─> __get_mtgjson_card_prices_generators()
    |           |
    |           ├─> For each generator:
    |           |   |
    |           |   └─> __generate_batch_insert_statement() (sql_like.py:101-144)
    |           |       |
    |           |       ├─> Accumulate rows (up to 2,000)
    |           |       ├─> create_insert_statement_body() [DB-specific]
    |           |       └─> Yield: "INSERT INTO ... VALUES\n(...),\n(...);"
    |           |
    |           └─> write_statements_to_file() [DB-specific]
    |               └─> Write to output file
    |
    v
Output Files
├─> MySQL: AllPrintings.sql, AllPricesToday.sql
├─> PostgreSQL: AllPrintings.psql, AllPricesToday.psql
├─> SQLite: AllPrintings.sqlite, AllPricesToday.sqlite
├─> CSV: csv/*.csv files
└─> Parquet: parquet/*.parquet files
```

## Important Line Numbers Summary

| What | File | Lines |
|------|------|-------|
| JSON loading | __main__.py | 150-151 |
| File vs directory detection | __main__.py | 122-142 |
| Set filtering | __main__.py | 153-156 |
| Date filtering | __main__.py | 158-163 |
| Converter instantiation | __main__.py | 165-168 |
| Data type enum | data_type.py | 5-6 |
| Batch INSERT generation | sql_like.py | 101-144 |
| Batch size config | sql_like.py | 17 |
| Generators selection | sql_like.py | 28-33 |
| Card generators list | sql_like.py | 40-81 |
| Schema dict generation | sql_like.py | 146-168 |
| Schema to SQL conversion | sql_like.py | 306-331 |
| Type inference | sql_like.py | 334-343 |
| MySQL escaping | mysql.py | 74-102 |
| PostgreSQL escaping | postgresql.py | 47-69 |
| SQLite execution | sqlite.py | 31, 78, 81 |
| CSV output | csv.py | 18-26 |
| Parquet output | parquet.py | 25-31 |
| Set field skipping | abstract.py | 23-30 |
| Card field skipping | abstract.py | 31-38 |

## Command Examples

### Basic MySQL conversion
```bash
python -m mtgsqlive -i AllPrintings.json -o output --mysql
```

### Convert with set filtering
```bash
python -m mtgsqlive -i AllPrintings.json -o output --mysql -s M10 M11 M12
```

### Convert sets after specific date
```bash
python -m mtgsqlive -i AllPrintings.json -o output --mysql --after-date 2024-01-01
```

### Convert individual JSON file
```bash
python -m mtgsqlive -i SPM.json -o output --mysql
```
(Note: Requires adding SPM to MtgjsonDataType enum first)

### All formats
```bash
python -m mtgsqlive -i AllPrintings.json -o output --all
```

### Japanese translation script
```bash
python -m mtgsqlive.scripts.find_missing_japanese_translations -i AllPrintings.json -o output --after-date 2024-01-01
```

## Key Concepts

### Batch INSERT Processing
- **Location**: sql_like.py, lines 101-144
- **Batch Size**: 2,000 rows (configurable)
- **Benefit**: Significantly faster database imports than single-row inserts
- **Process**: Accumulate rows, when batch size reached or all data exhausted, generate single INSERT with all rows

### Data Normalization
- **Denormalized JSON** -> **Normalized Relational Schema**
- Fields that contain arrays are broken into separate tables
- Example: Card with "legalities": {...} becomes separate entries in cardLegalities table
- Foreign language data normalized into separate cardForeignData table

### Generator Pattern
- **Purpose**: Memory efficiency - process millions of records without loading all into memory
- **Implementation**: Python generators yield data one record at a time
- **Example**: `get_next_card_like()` iterates through cards indefinitely as they're needed

### Schema-Driven Column Ordering
- **Location**: sql_like.py, lines 119-128
- **Benefit**: Ensures consistent column order in INSERT statements
- **Process**: All columns from schema, missing columns filled with NULL
- **Order**: Alphabetical sorting for consistency

## Project Structure Overview

```
mtgsqlive_raxelz/
├── mtgsqlive/
│   ├── __main__.py                          # Entry point
│   ├── __init__.py
│   ├── enums/
│   │   ├── __init__.py
│   │   └── data_type.py                     # Data type definitions
│   ├── converters/
│   │   ├── __init__.py
│   │   ├── mysql.py                         # MySQL converter
│   │   ├── postgresql.py                    # PostgreSQL converter
│   │   ├── sqlite.py                        # SQLite converter
│   │   ├── csv.py                           # CSV converter
│   │   ├── parquet.py                       # Parquet converter
│   │   └── parents/
│   │       ├── __init__.py
│   │       ├── abstract.py                  # Abstract base converter
│   │       ├── sql_like.py                  # SQL generation base
│   │       └── sqlite_based_converter.py    # SQLite-based converters
│   └── scripts/
│       └── find_missing_japanese_translations.py
├── SPM.json                                 # Individual set JSON file
├── output/                                  # Output directory
└── README.md
```

## Extending the Project: Adding SPM.json Support

### Current Status
- SPM.json file exists at project root
- __main__.py already supports individual JSON files
- Enum only defines AllPrintings and AllPricesToday

### Steps to Add Support

**Step 1**: Edit `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/enums/data_type.py`
```python
class MtgjsonDataType(enum.Enum):
    MTGJSON_CARDS = "AllPrintings"
    MTGJSON_CARD_PRICES = "AllPricesToday"
    MTGJSON_SPM = "SPM"  # Add this line
```

**Step 2**: Update `/Users/raxelz/Documents/Projects/mtgsqlive_raxelz/mtgsqlive/converters/parents/sql_like.py` (lines 28-33)
```python
def generate_database_insert_statements(self) -> Iterator[str]:
    if self.data_type in (MtgjsonDataType.MTGJSON_CARDS, MtgjsonDataType.MTGJSON_SPM):
        generators = self.__get_mtgjson_card_generators()
    elif self.data_type == MtgjsonDataType.MTGJSON_CARD_PRICES:
        generators = self.__get_mtgjson_card_prices_generators()
    else:
        raise ValueError()
    # ... rest of method
```

**Step 3**: Run
```bash
python -m mtgsqlive -i SPM.json -o output --mysql
```

