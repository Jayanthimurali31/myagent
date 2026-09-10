import pandas as pd

from src.create_ymal import build_metadata_document


def test_build_metadata_groups_source_details_under_physical_column():
    dataframe = pd.DataFrame(
        [
            {
                "Logical Table Name": "Orders",
                "Logical Column Name": "Order ID",
                "Physical Table Name": "ORDERS",
                "Physical Column Name": "order_id",
                "data type": "NUMBER",
                "length": "19",
                "precision": "0",
                "Null?": "NOT NULL",
                "Key": "PK",
                "Source System Code": "CRM",
                "Direct Source Column(s)": "order_id_src",
            },
            {
                "Logical Table Name": "Orders",
                "Logical Column Name": "Order ID",
                "Physical Table Name": "ORDERS",
                "Physical Column Name": "order_id",
                "data type": "NUMBER",
                "length": "19",
                "precision": "0",
                "Null?": "NOT NULL",
                "Key": "PK",
                "Source System Code": "ERP",
                "Direct Source Column(s)": "erp_order_id",
            },
        ]
    )

    metadata = build_metadata_document(dataframe)

    assert metadata["tables"][0]["name"] == "ORDERS"
    assert metadata["tables"][0]["columns"][0]["name"] == "order_id"
    assert metadata["tables"][0]["columns"][0]["logical_table_name"] == "Orders"
    assert metadata["tables"][0]["columns"][0]["logical_column_name"] == "Order ID"
    assert metadata["tables"][0]["columns"][0]["source_systems"] == [
        {
            "source_system_code": "CRM",
            "direct_source_columns": "order_id_src",
        },
        {
            "source_system_code": "ERP",
            "direct_source_columns": "erp_order_id",
        },
    ]
