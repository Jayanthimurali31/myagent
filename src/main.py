import json
from pathlib import Path

import pandas as pd
import yaml

REQUIRED_COLUMNS = [
    "Physical Table Name",
    "Physical Column Name",
    "data type",
    "length",
    "precision",
    "Null?",
    "Key",
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


def create_mappings(dataframe):
    table_names = sorted(
        name for name in dataframe["Physical Table Name"].unique() if name
    )
    table_mapping = {
        original: f"table_{index}"
        for index, original in enumerate(table_names, start=1)
    }

    column_names = sorted(
        name for name in dataframe["Physical Column Name"].unique() if name
    )
    column_mapping = {
        original: f"column_{index}"
        for index, original in enumerate(column_names, start=1)
    }
    return table_mapping, column_mapping


def build_mapping_document(table_mapping, column_mapping):
    return {
        "table_mapping": {
            "original_to_masked": table_mapping,
            "masked_to_original": {
                masked: original for original, masked in table_mapping.items()
            },
        },
        "column_mapping": {
            "original_to_masked": {
                original: masked
                for original, masked in column_mapping.items()
            },
            "masked_to_original": {
                masked: original
                for original, masked in column_mapping.items()
            },
        },
    }


def build_metadata_document(dataframe, table_mapping, column_mapping):
    tables = []
    for table_name, masked_table in table_mapping.items():
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        columns = []
        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name or any(
                column["name"] == column_mapping[column_name] for column in columns
            ):
                continue
            columns.append(
                {
                    "name": column_mapping[column_name],
                    "data_type": row["data type"] or None,
                    "length": row["length"] or None,
                    "precision": row["precision"] or None,
                    "nullable": row["Null?"] != "NOT NULL",
                    "key_type": {
                        "PK": "primary_key",
                        "FK": "foreign_key",
                    }.get(row["Key"].upper()) or None,
                }
            )
        tables.append({"name": masked_table, "columns": columns})

    relationships = []
    for table_name in table_mapping:
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name or "FK" not in row["Key"].upper():
                continue
            relationships.append(
                {
                    "child_table": table_mapping[table_name],
                    "child_column": column_mapping[column_name],
                    "parent_table": None,
                    "parent_column": None,
                }
            )
    return {
        "format_version": 1,
        "tables": tables,
        "relationships": relationships,
    }


def write_outputs(metadata_document, mapping_document, output_yaml, output_json):
    Path(output_yaml).write_text(
        yaml.safe_dump(metadata_document, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    Path(output_json).write_text(
        json.dumps(mapping_document, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main(input_file, sheet_name, output_yaml, output_json):
    dataframe = load_metadata(input_file, sheet_name)
    table_mapping, column_mapping = create_mappings(dataframe)
    metadata_document = build_metadata_document(
        dataframe, table_mapping, column_mapping
    )
    mapping_document = build_mapping_document(table_mapping, column_mapping)
    write_outputs(metadata_document, mapping_document, output_yaml, output_json)
    print(f"Generated: {output_yaml}")
    print(f"Generated: {output_json}")


if __name__ == "__main__":
    input_file = "data/Test.xlsx"
    sheet_name = "Mapping Columns"
    output_yaml = "data/masked_data_dictionary.yaml"
    output_json = "data/masking_mapping.json"
    main(
        input_file=input_file,
        sheet_name=sheet_name,
        output_yaml=output_yaml,
        output_json=output_json,
    )
