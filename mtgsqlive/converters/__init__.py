def __getattr__(name):
    if name == "MysqlConverter":
        from .mysql import MysqlConverter
        return MysqlConverter
    if name == "PostgresqlConverter":
        from .postgresql import PostgresqlConverter
        return PostgresqlConverter
    if name == "SqliteConverter":
        from .sqlite import SqliteConverter
        return SqliteConverter
    if name == "CsvConverter":
        from .csv import CsvConverter
        return CsvConverter
    if name == "ParquetConverter":
        from .parquet import ParquetConverter
        return ParquetConverter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
