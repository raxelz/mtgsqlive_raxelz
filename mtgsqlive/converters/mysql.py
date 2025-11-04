from datetime import datetime
from typing import Any, Dict, Iterator

import pymysql.converters

from .parents import SqlLikeConverter
from .parents.sql_like import MtgjsonDataType


class MysqlConverter(SqlLikeConverter):
    """A converter class that transforms MTGJSON data into MySQL-compatible SQL format.
    
    This class inherits from SqlLikeConverter and implements specific MySQL formatting
    and conversion logic. It handles the creation of SQL schema and data insertion
    statements in MySQL format.
    """

    def __init__(
        self, mtgjson_data: Dict[str, Any], output_dir: str, data_type: MtgjsonDataType, skip_schema: bool = False, output_filename: str = None
    ):
        """Initialize the MySQL converter.

        Args:
            mtgjson_data (Dict[str, Any]): The MTGJSON data to be converted
            output_dir (str): Directory where the output SQL file will be saved
            data_type (MtgjsonDataType): Type of MTGJSON data being processed
            skip_schema (bool): If True, skip schema creation and only generate INSERT statements
            output_filename (str): Optional custom output filename (without extension)
        """
        super().__init__(mtgjson_data, output_dir, data_type, skip_schema, output_filename)
        # Create output directory if it doesn't exist
        self.output_obj.root_dir.mkdir(parents=True, exist_ok=True)

        # Use custom filename if provided, otherwise use data_type.value
        filename = output_filename if output_filename else data_type.value
        self.output_obj.fp = self.output_obj.root_dir.joinpath(
            f"{filename}.sql"
        ).open("w", encoding="utf-8")

    def convert(self) -> None:
        """Convert MTGJSON data to MySQL format and write to output file.

        This method:
        1. Generates the SQL schema (if skip_schema is False)
        2. Creates the file header with metadata
        3. Writes the schema to the file (if skip_schema is False)
        4. Generates and writes the data insertion statements
        5. Commits the transaction
        """
        if self.skip_schema:
            # For single-set files, only generate INSERT statements
            header = "\n".join(
                (
                    "-- MTGSQLive Output File (Data Only)",
                    f"-- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"-- MTGJSON Version: {self.get_version()}",
                    "",
                    "START TRANSACTION;",
                    "",
                )
            )
            self.output_obj.fp.write(header)

            insert_data_generator = self.generate_database_insert_statements()
            self.write_statements_to_file(insert_data_generator)
            self.output_obj.fp.write("\nCOMMIT;")
        else:
            # For multi-set files, generate full schema + data
            sql_schema_as_dict = self._generate_sql_schema_dict()
            schema_query = self._convert_schema_dict_to_query(
                sql_schema_as_dict,
                engine="ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
                primary_key_op="INTEGER PRIMARY KEY AUTO_INCREMENT",
            )

            header = "\n".join(
                (
                    "-- MTGSQLive Output File",
                    f"-- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"-- MTGJSON Version: {self.get_version()}",
                    "",
                    "START TRANSACTION;",
                    "SET names 'utf8mb4';",
                    "",
                    schema_query,
                    "",
                    "COMMIT;",
                    "",
                    "",
                )
            )
            self.output_obj.fp.write(header)

            insert_data_generator = self.generate_database_insert_statements()
            self.write_statements_to_file(insert_data_generator)
            self.output_obj.fp.write("\nCOMMIT;")

    def create_insert_statement_body(self, data: Dict[str, Any]) -> str:
        """Create the body of an INSERT statement from the given data.

        Args:
            data (Dict[str, Any]): Dictionary containing the data to be inserted

        Returns:
            str: A comma-separated string of properly escaped values for the INSERT statement
        """
        pre_processed_values = []
        for value in data.values():
            if value is None:
                pre_processed_values.append("NULL")
                continue

            if isinstance(value, list):
                pre_processed_values.append(
                    '"'
                    + pymysql.converters.escape_string(", ".join(map(str, value)))
                    + '"'
                )
            elif isinstance(value, bool):
                pre_processed_values.append("1" if value else "0")
            else:
                pre_processed_values.append(
                    '"' + pymysql.converters.escape_string(str(value)) + '"'
                )

        return ", ".join(pre_processed_values)

    def write_statements_to_file(self, data_generator: Iterator[str]) -> None:
        """Write SQL statements to the output file.

        Args:
            data_generator (Iterator[str]): Generator yielding SQL statements to be written
        """
        for statement in data_generator:
            self.output_obj.fp.write(statement + "\n")
