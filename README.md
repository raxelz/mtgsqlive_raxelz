# MTGSQLive
A project to ETL MTGJSON data into multiple other consumer formats

# Connect With Us
Discord via [![Discord](https://img.shields.io/discord/224178957103136779.svg)](https://discord.gg/74GUQDE)

# About Us

MTGJSON and MTGSQLive are open sourced database creation and distribution tool for [*Magic: The Gathering*](https://magic.wizards.com/) cards.

You can find our documentation with all properties [here](https://mtgjson.com/data-models/).

To provide feedback or to report a bug, please [open a ticket](https://github.com/mtgjson/mtgsqlite/issues/new/).

If you would like to join or assist the development of the project, you can [join us on Discord](https://mtgjson.com/discord) to discuss things further.

# Setup and Installation

## Creating a Working Virtual Environment

Due to compatibility issues between some dependency versions and different Python versions, follow these specific steps for a working setup:

### Prerequisites
- Python 3.13+ (recommended)
- `AllPrintings.json` file in the project root directory

### Step-by-Step Setup

1. **Create a fresh virtual environment with Python 3.13:**
   ```bash
   python3 -m venv fresh_env
   ```

2. **Activate the virtual environment:**
   ```bash
   source fresh_env/bin/activate
   ```

3. **Install core dependencies:**
   ```bash
   pip install PyMySQL==1.1.0
   pip install pandas SQLAlchemy  # Use latest versions for Python 3.13 compatibility
   pip install pyarrow
   pip install mysql-connector-python==8.2.0 requests==2.31.0 setuptools==69.0.2
   ```

4. **Important**: Use the direct Python path to avoid shell aliases:
   ```bash
   fresh_env/bin/python -m mtgsqlive -i . -o output --mysql
   ```

### Compatibility Notes

- **Python 3.13**: Recommended for full compatibility with modern union type syntax (`|`)
- **Pandas**: Use the latest version instead of `pandas==2.1.3` from requirements.txt (compatibility issue with Python 3.13)
- **Input Parameter**: Use `-i .` (input directory) instead of `-i filename.json` (input file)

# Usage
```bash
$ pip install -r requirements.txt

$ python3 -m mtgsqlive [--args]

options:
  -h, --help            show this help message and exit
  -i INPUT_DIR, --input-dir INPUT_DIR
                        Path to directory that has MTGJSON compiled files, like AllPrintings.json and AllPricesToday.json
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Where to place translated files

Converters:
  --all                 Run all ETL operations
  --csv                 Compile CSV AllPrinting files
  --mysql               Compile AllPrintings.sql
  --parquet             Compile Parquet AllPrinting files
  --postgresql          Compile AllPrintings.psql
  --sqlite              Compile AllPrintings.sqlite
```

## Recent Changes

### Batch Insert SQL Generation

The SQL converters have been updated to use batch inserts instead of single row inserts for significantly improved performance. The batch size is set to 2,000 rows per INSERT statement. This change affects all SQL output formats (MySQL, PostgreSQL).

Run the following command to generate batch SQL:
```bash
source fresh_env/bin/activate
fresh_env/bin/python -m mtgsqlive -i AllPrintings.json -o output --mysql
```

### Japanese Translation Script

A new script has been added to find missing Japanese translations and generate SQL to fill in gaps:

```bash
fresh_env/bin/python -m mtgsqlive -i . -o output --mysql
```

**Prerequisites:**
- `AllPrintings.json` must be present in the project root directory

**What it does:**
1. Analyzes all cards in the MTGJSON data to find which cards lack Japanese translations
2. Cross-references cards without translations against other cards that might have the same translation available
3. Generates three output files in the `output/` directory:
   - `found_japanese_translations.csv` - Cards where translations were found from other sets
   - `missing_japanese_translations.csv` - Cards with no available Japanese translation
   - `insert_japanese_translations.sql` - MySQL-compatible SQL file with batch INSERT statements to add the found translations

**Output:**
The script will create an `output/` directory and generate:
- CSV files for analysis and review
- A MySQL SQL file with `INSERT INTO cardForeignData` statements using batch inserts (1,000 rows per batch)
- Uses `ON DUPLICATE KEY UPDATE` to handle existing translations gracefully

The generated SQL file includes proper escaping for Japanese text and can be executed directly against a MySQL database created from the MTGSQLive output.