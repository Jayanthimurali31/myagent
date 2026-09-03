import json
from pathlib import Path

import pandas as pd

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


def render_markdown(dataframe, table_mapping, column_mapping):
    lines = [
        "# Masked Data Dictionary",
        "",
        "This file contains masked names only. Use masking_mapping.json to restore original names.",
        "",
    ]

    for table_name, masked_table in table_mapping.items():
        lines.extend([f"## {masked_table}", ""])
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        rendered_columns = set()
        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name or column_name in rendered_columns:
                continue
            rendered_columns.add(column_name)
            masked_column = column_mapping[column_name]
            lines.extend(
                [
                    f"### {masked_column}",
                    f"data_type: {row['data type']}",
                    f"length: {row['length']}",
                    f"precision: {row['precision']}",
                    f"nullable: {row['Null?']}",
                    f"key: {row['Key']}",
                    "",
                ]
            )

    lines.append("## Relationships")
    lines.append("")
    rendered_relationships = set()
    for table_name in table_mapping:
        table_rows = dataframe[dataframe["Physical Table Name"] == table_name]
        for _, row in table_rows.iterrows():
            column_name = row["Physical Column Name"]
            if not column_name:
                continue
            masked_column = column_mapping[column_name]
            relationship = (table_name, column_name)
            if "FK" not in row["Key"].upper() or relationship in rendered_relationships:
                continue
            rendered_relationships.add(relationship)
            lines.append(f"- table: {table_mapping[table_name]}")
            lines.append(f"  column: {masked_column}")
            lines.append("  type: foreign_key")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(markdown, mapping_document, output_md, output_json):
    Path(output_md).write_text(markdown, encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(mapping_document, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main(input_file, sheet_name, output_md, output_json):
    dataframe = load_metadata(input_file, sheet_name)
    table_mapping, column_mapping = create_mappings(dataframe)
    markdown = render_markdown(dataframe, table_mapping, column_mapping)
    mapping_document = build_mapping_document(table_mapping, column_mapping)
    write_outputs(markdown, mapping_document, output_md, output_json)
    print(f"Generated: {output_md}")
    print(f"Generated: {output_json}")


if __name__ == "__main__":
    input_file = "data/Test.xlsx"
    sheet_name = "Mapping Columns"
    output_md = "data/masked_data_dictionary.md"
    output_json = "data/masking_mapping.json"
    main(input_file=input_file, sheet_name=sheet_name, output_md=output_md, output_json=output_json)
