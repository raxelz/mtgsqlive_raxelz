from datetime import datetime
from typing import Any, Dict, Iterator

import pymysql

from ..enums import MtgjsonDataType
from .parents import SqlLikeConverter


class PostgresqlConverter(SqlLikeConverter):
    def __init__(
        self, mtgjson_data: Dict[str, Any], output_dir: str, data_type: MtgjsonDataType, skip_schema: bool = False, output_filename: str = None
    ) -> None:
        super().__init__(mtgjson_data, output_dir, data_type, skip_schema, output_filename)

        # Use custom filename if provided, otherwise use data_type.value
        filename = output_filename if output_filename else data_type.value
        self.output_obj.fp = self.output_obj.root_dir.joinpath(
            f"{filename}.psql"
        ).open("w", encoding="utf-8")

    def convert(self) -> None:
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
        else:
            # For multi-set files, generate full schema + data
            sql_schema_as_dict = self._generate_sql_schema_dict()
            schema_query = self._convert_schema_dict_to_query(
                sql_schema_as_dict,
                engine="",
                primary_key_op="SERIAL PRIMARY KEY",
            )

            header = "\n".join(
                (
                    "-- MTGSQLive Output File",
                    f"-- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"-- MTGJSON Version: {self.get_version()}",
                    "",
                    "START TRANSACTION;",
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

    def create_insert_statement_body(self, data: Dict[str, Any]) -> str:
        pre_processed_values = []
        for value in data.values():
            if not value:
                pre_processed_values.append("NULL")
                continue

            if isinstance(value, list):
                statement = (
                    pymysql.converters.escape_string(", ".join(map(str, value)))
                    .replace("\\'", "''")
                    .replace('\\"', '"')
                )
                pre_processed_values.append(f"'{statement}'")
            else:
                statement = (
                    pymysql.converters.escape_string(str(value))
                    .replace("\\'", "''")
                    .replace('\\"', '"')
                )
                pre_processed_values.append(f"'{statement}'")

        return ", ".join(pre_processed_values)

    def write_statements_to_file(self, data_generator: Iterator[str]) -> None:
        statements = []
        for statement in data_generator:
            statements.append(statement)
            if len(statements) >= 1_000:
                self.output_obj.fp.writelines(statements)
                statements = []
        self.output_obj.fp.writelines(statements)
