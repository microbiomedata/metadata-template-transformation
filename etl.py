import os
import json

import pandas as pd
import click
import requests

from typing import Dict, Any, List, Union, Optional
from dotenv import load_dotenv


class MetadataRetriever:
    """
    Retrieves metadata records from a given submission ID and user facility.
    """

    USER_FACILITY_DICT: Dict[str, str] = {
        "emsl": "emsl_data",
        "jgi_mg": "jgi_mg_data",
        "jgi_mt": "jgi_mt_data",
    }

    def __init__(self, metadata_submission_id: str, user_facility: str) -> None:
        """
        Initialize the MetadataRetriever.

        :param metadata_submission_id: The ID of the metadata submission.
        :param user_facility: The user facility to retrieve data from.
        """
        self.metadata_submission_id = metadata_submission_id
        self.user_facility = user_facility
        self.env: Dict[str, str] = dict(os.environ)

    def retrieve_metadata_records(self, unique_field: str) -> pd.DataFrame:
        """
        Retrieves the metadata records for the given submission ID and user facility.

        :return: The retrieved metadata records as a Pandas DataFrame.
        """
        response: Dict[str, Any] = requests.get(
            f"https://data.microbiomedata.org/api/metadata_submission/{self.metadata_submission_id}",
            cookies={"session": self.env["DATA_PORTAL_COOKIE"]},
        ).json()

        if "soil_data" in response["metadata_submission"]["sampleData"]:
            soil_data: List[Dict[str, Any]] = response["metadata_submission"][
                "sampleData"
            ]["soil_data"]
            soil_data_df: pd.DataFrame = pd.DataFrame(soil_data)
        else:
            soil_data_df = pd.DataFrame()

        common_df: pd.DataFrame = pd.DataFrame()
        if self.user_facility in self.USER_FACILITY_DICT:
            user_facility_data: Dict[str, Any] = response["metadata_submission"][
                "sampleData"
            ].get(self.USER_FACILITY_DICT[self.user_facility], {})
            common_df = pd.DataFrame(user_facility_data)

        if soil_data_df.empty and not common_df.empty:
            df = common_df
        elif common_df.empty and not soil_data_df.empty:
            df = soil_data_df
        elif not common_df.empty and not soil_data_df.empty:
            common_cols: List[str] = list(
                set(common_df.columns.to_list()) & set(soil_data_df.columns.to_list())
            )
            if unique_field in common_cols:
                common_cols.remove(unique_field)

            common_df = common_df.drop(columns=common_cols)
            df = pd.merge(soil_data_df, common_df, on=unique_field)
        else:
            raise ValueError(
                f"The submission metadata record: {self.metadata_submission_id} is empty."
            )

        return df


class SpreadsheetCreator:
    """
    Creates a spreadsheet based on a JSON mapper and metadata DataFrame.
    """

    def __init__(
        self,
        json_mapper: Dict[str, Dict[str, Union[str, List[str]]]],
        metadata_df: pd.DataFrame,
    ) -> None:
        """
        Initialize the SpreadsheetCreator.

        :param json_mapper: The JSON mapper specifying column mappings.
        :param metadata_df: The metadata DataFrame to create the spreadsheet from.
        """
        self.json_mapper = json_mapper
        self.metadata_df = metadata_df

    def combine_headers_df(self, header: bool) -> pd.DataFrame:
        """
        Combines and formats the headers DataFrame.

        :param header: True if the headers should be included, False otherwise.
        :return: The combined headers DataFrame.
        """
        d: Dict[str, List[Union[str, List[str]]]] = {}
        for k, v in self.json_mapper.items():
            l: List[Union[str, List[str]]] = [
                h for h_n, h in v.items() if h_n != "sub_port_mapping"
            ]
            d[k] = l

        headers_df: pd.DataFrame = pd.DataFrame(d)

        if header:
            last_row = headers_df.iloc[-1]
            column_values: List[str] = list(last_row)

            headers_df = headers_df.drop(headers_df.index[-1])
            headers_df.loc[len(headers_df)] = headers_df.columns.to_list()
            headers_df.columns = column_values

            shift = 1
            headers_df = pd.concat(
                [headers_df.iloc[-shift:], headers_df.iloc[:-shift]], ignore_index=True
            )

        return headers_df

    def combine_sample_rows_df(self) -> pd.DataFrame:
        """
        Combines and formats the sample rows DataFrame.

        :return: The combined sample rows DataFrame.
        """
        rows_df: pd.DataFrame = pd.DataFrame()
        for k, v in self.json_mapper.items():
            if (
                "sub_port_mapping" in v
                and v["sub_port_mapping"] in self.metadata_df.columns.to_list()
            ):
                if "header" in v:
                    rows_df[v["header"]] = self.metadata_df[v["sub_port_mapping"]]
                else:
                    rows_df[k] = self.metadata_df[v["sub_port_mapping"]]

        return rows_df

    def combine_headers_and_rows(
        self, headers_df: pd.DataFrame, rows_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Combines the headers and sample rows DataFrames.

        :param headers_df: The headers DataFrame.
        :param rows_df: The sample rows DataFrame.
        :return: The combined DataFrame.
        """
        return pd.concat([headers_df, rows_df])

    def create_spreadsheet(self, header: bool) -> pd.DataFrame:
        """
        Creates the spreadsheet based on the JSON mapper and metadata DataFrame.

        :param header: True if the headers should be included, False otherwise.
        :return: The created spreadsheet.
        """
        headers_df = self.combine_headers_df(header)
        rows_df = self.combine_sample_rows_df()
        spreadsheet = self.combine_headers_and_rows(headers_df, rows_df)
        return spreadsheet


@click.command()
@click.option("--submission", "-s", required=True, help="Metadata submission id.")
@click.option(
    "--user-facility", "-u", required=True, help="User facility to send data to."
)
@click.option("--header/--no-header", "-h", default=False, show_default=True)
@click.option(
    "--mapper",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to user facility specific JSON file.",
)
@click.option(
    "--unique-field",
    "-uf",
    required=True,
    help="Unique field to identify the metadata records.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to result output XLSX file.",
)
def cli(
    submission: str,
    user_facility: str,
    header: bool,
    mapper: str,
    unique_field: str,
    output: str,
) -> None:
    """
    Command-line interface for creating a spreadsheet based on metadata records.

    :param submission: The ID of the metadata submission.
    :param user_facility: The user facility to retrieve data from.
    :param header: True if the headers should be included, False otherwise.
    :param mapper: Path to the JSON mapper specifying column mappings.
    :param unique_field: Unique field to identify the metadata records.
    :param output: Path to the output XLSX file.
    """
    load_dotenv()
    metadata_retriever = MetadataRetriever(submission, user_facility)
    metadata_df = metadata_retriever.retrieve_metadata_records(unique_field)

    with open(mapper, "r") as f:
        json_mapper: Dict[str, Dict[str, Union[str, List[str]]]] = json.load(f)

    spreadsheet_creator = SpreadsheetCreator(json_mapper, metadata_df)
    user_facility_spreadsheet = spreadsheet_creator.create_spreadsheet(header)
    user_facility_spreadsheet.to_excel(output, index=False)


if __name__ == "__main__":
    cli()
