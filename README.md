# MTGSQLive
ETL tool to convert MTGJSON data into SQL, CSV, Parquet, and SQLite formats.

**Documentation**: [mtgjson.com/data-models](https://mtgjson.com/data-models/)
**Discord**: [![Discord](https://img.shields.io/discord/224178957103136779.svg)](https://discord.gg/74GUQDE)
**Issues**: [github.com/mtgjson/mtgsqlite/issues](https://github.com/mtgjson/mtgsqlite/issues/new/)

# Setup

## Installation

```bash
# Create virtual environment (Python 3.13+ recommended)
python3 -m venv fresh_env
source fresh_env/bin/activate

# Install dependencies
pip install PyMySQL==1.1.0 pandas SQLAlchemy pyarrow
pip install mysql-connector-python==8.2.0 requests==2.31.0 setuptools==69.0.2
```

# Usage

## Basic Examples

```bash
# Generate SQL for all sets (creates AllPrintings.sql with full schema)
python3 -m mtgsqlive -i AllPrintings.json -o output --mysql

# Generate SQL for a single set (creates SPM.sql with data only, no schema)
python3 -m mtgsqlive -i SPM.json -o output --mysql

# Process directory with multiple JSON files
python3 -m mtgsqlive -i /path/to/json/dir -o output --all

# Filter specific sets
python3 -m mtgsqlive -i AllPrintings.json -o output --mysql --sets SPM NEO

# Filter by release date
python3 -m mtgsqlive -i AllPrintings.json -o output --mysql --after-date 2024-01-01
```

## File Type Detection

The tool automatically detects file types:
- **Single-set files** (e.g., `SPM.json`): Generates data-only INSERT statements, output named by set code
- **Multi-set files** (e.g., `AllPrintings.json`): Generates full schema + data, output named by data type

## Options

```
-i, --input-dir       Path to JSON file or directory
-o, --output-dir      Output directory (default: /tmp/mtgsqlive)
-s, --sets           Filter specific set codes (space-separated)
--after-date         Only include sets after date (YYYY-MM-DD)

Converters:
--mysql              Generate MySQL SQL file
--postgresql         Generate PostgreSQL SQL file
--sqlite             Generate SQLite database
--csv                Generate CSV files
--parquet            Generate Parquet files
--all                Run all converters
```

# Features

## Single-Set File Support
Automatically processes individual set JSON files (e.g., `SPM.json`) and generates data-only SQL with set-specific filenames. Includes all related data: cards, tokens, identifiers, legalities, rulings, foreign data, translations, and booster configurations.

## Batch Insert Performance
SQL converters use batch inserts (2,000 rows per statement) for improved performance across MySQL, PostgreSQL, and SQLite.

## Booster/Box Data Extraction
Automatically extracts booster configuration into 4 tables: `setBoosterContents`, `setBoosterContentWeights`, `setBoosterSheets`, and `setBoosterSheetCards`. Includes sheet compositions, weights, and individual card distributions.

## Date Filtering
Filter sets by release date to generate incremental updates or focus on recent releases:
```bash
python3 -m mtgsqlive -i AllPrintings.json -o output --mysql --after-date 2024-01-01
```

## Japanese Translation Script
Find and generate SQL for missing Japanese translations:
```bash
python3 -m mtgsqlive.scripts.find_missing_japanese_translations --after-date 2024-07-20
```

**Output:**
- `found_japanese_translations.csv` - Translations found from other sets
- `missing_japanese_translations.csv` - Cards with no available translation
- `insert_japanese_translations.sql` - Batch INSERT statements (1,000 rows per batch)