import json
import re
from pathlib import Path

import yaml

REQUIRED_TEST_CASE_FIELDS = {
    "id",
    "category",
    "name",
    "objective",
    "priority",
    "tables",
    "columns",
    "expected_result",
    "sql",
}


def load_yaml(path):
    with Path(path).open(encoding="utf-8") as file:
        document = yaml.safe_load(file)
    if not isinstance(document, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return document


def load_mapping(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        table_mapping = document["table_mapping"]["masked_to_original"]
        column_mapping = document["column_mapping"]["masked_to_original"]
    except KeyError as error:
        raise ValueError(f"Mapping JSON is missing {error.args[0]}") from error
    if not isinstance(table_mapping, dict) or not isinstance(column_mapping, dict):
        raise ValueError("Mapping JSON reverse mappings must be objects")
    return table_mapping, column_mapping


def replace_identifiers(value, table_mapping, column_mapping):
    if isinstance(value, dict):
        return {
            key: replace_identifiers(item, table_mapping, column_mapping)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            replace_identifiers(item, table_mapping, column_mapping)
            for item in value
        ]
    if not isinstance(value, str):
        return value

    replacements = {**table_mapping, **column_mapping}
    if not replacements:
        return value
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:%s)(?![A-Za-z0-9_])"
        % "|".join(re.escape(identifier) for identifier in replacements)
    )
    return pattern.sub(lambda match: replacements[match.group(0)], value)


def validate_test_cases(document):
    test_cases = document.get("test_cases")
    if not isinstance(test_cases, list):
        raise ValueError("Test-case YAML must contain a test_cases list")
    for index, test_case in enumerate(test_cases, start=1):
        if not isinstance(test_case, dict):
            raise ValueError(f"Test case {index} must be an object")
        missing = REQUIRED_TEST_CASE_FIELDS - test_case.keys()
        if missing:
            raise ValueError(
                f"Test case {index} is missing fields: {sorted(missing)}"
            )
    return test_cases


def build_unmasked_document(test_cases_document, table_mapping, column_mapping):
    validate_test_cases(test_cases_document)
    return replace_identifiers(
        test_cases_document,
        table_mapping,
        column_mapping,
    )


def render_sql(document):
    lines = []
    for test_case in document["test_cases"]:
        lines.append(
            f"-- {test_case['id']} | {test_case['category']} | {test_case['name']}"
        )
        lines.append(test_case["sql"].rstrip())
        lines.append("")
    return "\n".join(lines)


def write_outputs(document, output_yaml, output_sql):
    Path(output_yaml).write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    Path(output_sql).write_text(render_sql(document), encoding="utf-8")


def main(
    input_test_cases,
    input_mapping,
    output_yaml,
    output_sql,
):
    test_cases_document = load_yaml(input_test_cases)
    table_mapping, column_mapping = load_mapping(input_mapping)
    unmasked_document = build_unmasked_document(
        test_cases_document,
        table_mapping,
        column_mapping,
    )
    write_outputs(unmasked_document, output_yaml, output_sql)
    print(f"Generated: {output_yaml}")
    print(f"Generated: {output_sql}")


if __name__ == "__main__":
    default_test_cases = "data/test_cases.yaml"
    default_mapping = "data/masking_mapping.json"
    default_output_yaml = "data/unmasked_test_cases.yaml"
    default_output_sql = "data/unmasked_test_cases.sql"
    main(input_test_cases=default_test_cases, input_mapping=default_mapping, output_yaml=default_output_yaml, output_sql=default_output_sql)
