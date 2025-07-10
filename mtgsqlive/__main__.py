import argparse
import json
import logging
import pathlib
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict

from mtgsqlive.converters import (
    CsvConverter,
    MysqlConverter,
    ParquetConverter,
    PostgresqlConverter,
    SqliteConverter,
)
from mtgsqlive.enums.data_type import MtgjsonDataType

TOP_LEVEL_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
LOG_DIR: pathlib.Path = TOP_LEVEL_DIR.joinpath("logs")
LOGGER = logging.getLogger(__name__)


def init_logger() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(asctime)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                str(
                    LOG_DIR.joinpath(
                        "mtgsqlive_"
                        + str(datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
                        + ".log"
                    )
                )
            ),
        ],
    )


def get_converters() -> Dict[str, Any]:
    return OrderedDict(
        {
            "mysql": MysqlConverter,
            "postgresql": PostgresqlConverter,
            "sqlite": SqliteConverter,
            "csv": CsvConverter,
            "parquet": ParquetConverter,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        required=True,
        help="Path to directory that has MTGJSON compiled files, like AllPrintings.json and AllPricesToday.json",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="/tmp/mtgsqlive",
        help="Where to place translated files",
    )
    parser.add_argument(
        "-s",
        "--sets",
        type=str.upper,
        nargs="*",
        help="Transpose specific sets instead of all sets",
    )
    parser.add_argument(
        "--after-date",
        type=str,
        help="Only include sets released after this date (format: YYYY-MM-DD)",
    )

    converter_group = parser.add_argument_group(title="Converters")
    converter_group.add_argument(
        "--all", action="store_true", help="Run all ETL operations"
    )
    converter_group.add_argument(
        "--csv", action="store_true", help="Compile CSV AllPrinting files"
    )
    converter_group.add_argument(
        "--mysql", action="store_true", help="Compile AllPrintings.sql"
    )
    converter_group.add_argument(
        "--parquet", action="store_true", help="Compile Parquet AllPrinting files"
    )
    converter_group.add_argument(
        "--postgresql", action="store_true", help="Compile AllPrintings.psql"
    )
    converter_group.add_argument(
        "--sqlite", action="store_true", help="Compile AllPrintings.sqlite"
    )

    return parser.parse_args()


def main() -> None:
    init_logger()

    args = parse_args()

    converters_map = get_converters()
    if not args.all:
        for converter_input_param in converters_map.copy().keys():
            if not getattr(args, converter_input_param):
                del converters_map[converter_input_param]

    mtgjson_input_path = pathlib.Path(args.input_dir).expanduser()
    
    # Handle both file and directory inputs
    if mtgjson_input_path.is_file():
        # If input is a file, use its parent directory and process only that file
        mtgjson_input_dir = mtgjson_input_path.parent
        filename = mtgjson_input_path.stem  # Get filename without extension
        
        # Find matching data type
        matching_data_type = None
        for data_type in MtgjsonDataType:
            if data_type.value == filename:
                matching_data_type = data_type
                break
        
        if matching_data_type is None:
            LOGGER.error(f"Unknown file type: {filename}")
            return
            
        data_types_to_process = [matching_data_type]
    else:
        # If input is a directory, process all data types
        mtgjson_input_dir = mtgjson_input_path
        data_types_to_process = list(MtgjsonDataType)
    
    for data_type in data_types_to_process:
        mtgjson_input_file = mtgjson_input_dir.joinpath(f"{data_type.value}.json")
        if not mtgjson_input_file.exists():
            LOGGER.error(f"Cannot locate {mtgjson_input_file}, skipping.")
            continue

        with mtgjson_input_file.open(encoding="utf-8") as fp:
            mtgjson_input_data = json.load(fp)

        if args.sets:
            for set_key in list(mtgjson_input_data["data"].keys()):
                if set_key not in args.sets:
                    del mtgjson_input_data["data"][set_key]

        if args.after_date:
            for set_key in list(mtgjson_input_data["data"].keys()):
                set_data = mtgjson_input_data["data"][set_key]
                release_date = set_data.get("releaseDate", "")
                if release_date <= args.after_date:
                    del mtgjson_input_data["data"][set_key]

        for converter in converters_map.values():
            LOGGER.info(f"Converting {data_type.value} via {converter.__name__}")
            converter(mtgjson_input_data, args.output_dir, data_type).convert()
            LOGGER.info(f"Converted {data_type.value} via {converter.__name__}")


if __name__ == "__main__":
    main()
