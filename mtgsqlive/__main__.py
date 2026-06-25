import argparse
import json
import logging
import pathlib
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict

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
    def _mysql():
        from mtgsqlive.converters.mysql import MysqlConverter
        return MysqlConverter

    def _postgresql():
        from mtgsqlive.converters.postgresql import PostgresqlConverter
        return PostgresqlConverter

    def _sqlite():
        from mtgsqlive.converters.sqlite import SqliteConverter
        return SqliteConverter

    def _csv():
        from mtgsqlive.converters.csv import CsvConverter
        return CsvConverter

    def _parquet():
        from mtgsqlive.converters.parquet import ParquetConverter
        return ParquetConverter

    return OrderedDict(
        {
            "mysql": _mysql,
            "postgresql": _postgresql,
            "sqlite": _sqlite,
            "csv": _csv,
            "parquet": _parquet,
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
        # If input is a file, load it and check its structure
        with mtgjson_input_path.open(encoding="utf-8") as fp:
            loaded_data = json.load(fp)

        # Check if this is a single-set file or a multi-set file
        is_single_set = False
        if "data" in loaded_data and isinstance(loaded_data["data"], dict):
            # Check if data contains a single set (has 'code' or 'baseSetSize' keys)
            # rather than being a dictionary of sets
            if "code" in loaded_data["data"] or "baseSetSize" in loaded_data["data"]:
                is_single_set = True

        if is_single_set:
            # Wrap single-set data into AllPrintings format
            set_code = loaded_data["data"].get("code", mtgjson_input_path.stem.upper())
            LOGGER.info(f"Detected single-set file for set: {set_code}")

            files_to_process = [(
                MtgjsonDataType.MTGJSON_CARDS,
                {
                    "meta": loaded_data.get("meta", {}),
                    "data": {set_code: loaded_data["data"]}
                },
                True,  # skip_schema flag for single-set files
                set_code  # output_filename for single-set files
            )]
        else:
            # Multi-set file - find matching data type
            filename = mtgjson_input_path.stem
            matching_data_type = None
            for data_type in MtgjsonDataType:
                if data_type.value == filename:
                    matching_data_type = data_type
                    break

            if matching_data_type is None:
                LOGGER.error(f"Unknown file type: {filename}")
                return

            files_to_process = [(matching_data_type, loaded_data, False, None)]  # Don't skip schema, use default filename
    else:
        # If input is a directory, process all data types
        mtgjson_input_dir = mtgjson_input_path
        files_to_process = []

        for data_type in MtgjsonDataType:
            mtgjson_input_file = mtgjson_input_dir.joinpath(f"{data_type.value}.json")
            if not mtgjson_input_file.exists():
                LOGGER.error(f"Cannot locate {mtgjson_input_file}, skipping.")
                continue

            with mtgjson_input_file.open(encoding="utf-8") as fp:
                mtgjson_input_data = json.load(fp)

            files_to_process.append((data_type, mtgjson_input_data, False, None))  # Don't skip schema, use default filename

    # Process all files
    for data_type, mtgjson_input_data, skip_schema, output_filename in files_to_process:

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

        for converter_loader in converters_map.values():
            converter = converter_loader()
            LOGGER.info(f"Converting {data_type.value} via {converter.__name__}")
            converter(mtgjson_input_data, args.output_dir, data_type, skip_schema, output_filename).convert()
            LOGGER.info(f"Converted {data_type.value} via {converter.__name__}")


if __name__ == "__main__":
    main()
