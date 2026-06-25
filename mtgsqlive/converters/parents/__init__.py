from .abstract import AbstractConverter
from .sql_like import SqlLikeConverter


def __getattr__(name):
    if name == "SqliteBasedConverter":
        from .sqlite_based_converter import SqliteBasedConverter
        return SqliteBasedConverter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
