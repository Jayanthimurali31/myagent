import pandas as pd
from pathlib import Path


INPUT_FILE = "data/Test.xlsx"
SHEET_NAME = "Mapping Columns"
OUTPUT_MD = "data/masked_data_dictionary.md"


def clean_value(v):
    if pd.isna(v):
        return ""
    return str(v).replace("\n", " ").replace("\r", " ").strip()


# --------------------------------------------------
# Read Excel
# --------------------------------------------------

df = pd.read_excel(
    INPUT_FILE,
    sheet_name=SHEET_NAME,
    dtype=str,
    skiprows=2
)

df.columns = [c.strip() for c in df.columns]

required_columns = [
    "Physical Table Name",
    "Physical Column Name",
    "data type",
    "length",
    "precision",
    "Null?",
    "Key"
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise Exception(f"Missing columns: {missing}")

# print(df.head())

# --------------------------------------------------
# Create table mapping
# --------------------------------------------------

tables = (
    df["Physical Table Name"]
    .dropna()
    .astype(str)
    .unique()
)
# print(tables)
table_mapping = {}

for idx, table_name in enumerate(sorted(tables), start=1):
    table_mapping[table_name] = f"table_{idx}"


# --------------------------------------------------
# Create column mapping
# --------------------------------------------------

column_mapping = {}
relationship_candidates = []

for table_name in sorted(tables):

    masked_table = table_mapping[table_name]

    table_df = (
        df[df["Physical Table Name"] == table_name]
        .reset_index(drop=True)
    )

    counter = 1

    for _, row in table_df.iterrows():

        physical_column = clean_value(
            row["Physical Column Name"]
        )

        if physical_column == "":
            continue

        masked_column = f"column_{masked_table.split('_')[1]}_{counter}"

        column_mapping[
            (table_name, physical_column)
        ] = masked_column

        key_value = clean_value(row["Key"])

        if "FK" in key_value.upper():
            relationship_candidates.append(
                {
                    "table": masked_table,
                    "column": masked_column,
                    "original_column": physical_column
                }
            )

        counter += 1


# --------------------------------------------------
# Markdown generation
# --------------------------------------------------

md = []

md.append("# Masked Data Dictionary\n")

# --------------------------------------------------
# Table Mapping Section
# --------------------------------------------------

md.append("## Table Mapping\n")

md.append("| Masked Table | Original Table |")
md.append("|-------------|----------------|")

for original, masked in table_mapping.items():
    md.append(f"| {masked} | MASKED |")

md.append("\n")


# --------------------------------------------------
# Table Definitions
# --------------------------------------------------

for table_name in sorted(tables):

    masked_table = table_mapping[table_name]

    md.append(f"## {masked_table}\n")

    md.append(
        "| Masked Column | Data Type | Length | Precision | Null | Key |"
    )
    md.append(
        "|---------------|-----------|--------|-----------|------|-----|"
    )

    table_df = (
        df[df["Physical Table Name"] == table_name]
        .reset_index(drop=True)
    )

    for _, row in table_df.iterrows():

        physical_column = clean_value(
            row["Physical Column Name"]
        )

        if physical_column == "":
            continue

        masked_column = column_mapping[
            (table_name, physical_column)
        ]

        datatype = clean_value(row["data type"])
        length = clean_value(row["length"])
        precision = clean_value(row["precision"])
        nullable = clean_value(row["Null?"])
        key = clean_value(row["Key"])

        md.append(
            f"| {masked_column} | "
            f"{datatype} | "
            f"{length} | "
            f"{precision} | "
            f"{nullable} | "
            f"{key} |"
        )

    md.append("\n")


# --------------------------------------------------
# Relationships
# --------------------------------------------------

md.append("## Relationships\n")

for rel in relationship_candidates:

    md.append(
        f"- {rel['table']}.{rel['column']} "
        f"(FK)"
    )

md.append("\n")


# --------------------------------------------------
# Save file
# --------------------------------------------------

Path(OUTPUT_MD).write_text(
    "\n".join(md),
    encoding="utf-8"
)

print(f"Generated: {OUTPUT_MD}")
