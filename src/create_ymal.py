from pathlib import Path

import pandas as pd
import yaml

REQUIRED_COLUMNS = [
    "Logical Table Name",
    "Logical Column Name",
    "Physical Table Name",
    "Physical Column Name",
    "data type",
    "length",
    "precision",
    "Null?",
    "Key",
    "Source System Code",
    "Direct Source Column(s)",
]


def clean_value(value):
    """Convert spreadsheet values to stable, single-line strings."""
    if pd.isna(value):
        return ""
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def load_metadata(input_file, sheet_name):
    dataframe = pd.read_excel(
        input_file,
        sheet_name=sheet_name,
        dtype=str,
        skiprows=2,
    )
    dataframe.columns = [clean_value(column) for column in dataframe.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    for column in REQUIRED_COLUMNS:
        dataframe[column] = dataframe[column].map(clean_value)
    return dataframe


def build_metadata_document(dataframe):
    tables = []
    for table_name in sorted(
        name for name in dataframe["Physical Table Name"].unique() if name
    ):
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        columns = []
        columns_by_name = {}

        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name:
                continue

            if column_name not in columns_by_name:
                column_entry = {
                    "name": column_name,
                    "logical_table_name": row["Logical Table Name"] or None,
                    "logical_column_name": row["Logical Column Name"] or None,
                    "data_type": row["data type"] or None,
                    "length": row["length"] or None,
                    "precision": row["precision"] or None,
                    "nullable": row["Null?"] != "NOT NULL",
                    "key_type": {
                        "PK": "primary_key",
                        "FK": "foreign_key",
                    }.get((row["Key"] or "").upper()) or None,
                    "source_systems": [],
                }
                columns_by_name[column_name] = column_entry
                columns.append(column_entry)

            source_entry = {
                "source_system_code": row["Source System Code"] or None,
                "direct_source_columns": row["Direct Source Column(s)"] or None,
            }
            if source_entry["source_system_code"] or source_entry["direct_source_columns"]:
                columns_by_name[column_name]["source_systems"].append(source_entry)

        tables.append({"name": table_name, "columns": columns})

    relationships = []
    for table_name in sorted(
        name for name in dataframe["Physical Table Name"].unique() if name
    ):
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name or "FK" not in (row["Key"] or "").upper():
                continue
            relationships.append(
                {
                    "child_table": table_name,
                    "child_column": column_name,
                    "parent_table": None,
                    "parent_column": None,
                }
            )
    return {
        "format_version": 1,
        "tables": tables,
        "relationships": relationships,
    }


def write_outputs(metadata_document, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for table in metadata_document["tables"]:
        table_name = table["name"]
        file_path = output_path / f"{table_name}.yaml"
        table_document = {
            "format_version": metadata_document["format_version"],
            "table": table,
            "relationships": [
                relationship
                for relationship in metadata_document["relationships"]
                if relationship["child_table"] == table_name
            ],
        }
        file_path.write_text(
            yaml.safe_dump(table_document, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )


def main(input_file, sheet_name, output_yaml):
    dataframe = load_metadata(input_file, sheet_name)
    metadata_document = build_metadata_document(dataframe)
    write_outputs(metadata_document, output_yaml)
    print(f"Generated files in: {output_yaml}")


if __name__ == "__main__":
    input_file = "data/Test.xlsx"
    sheet_name = "Mapping Columns"
    output_yaml = "data/metadata_output"
    main(
        input_file=input_file,
        sheet_name=sheet_name,
        output_yaml=output_yaml,
    )
