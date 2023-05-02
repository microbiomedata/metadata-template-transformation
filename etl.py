import pandas as pd
import os
import json
import warnings
import click
import dotenv
import requests

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def load_dotenv():
    env_path = dotenv.find_dotenv()
    if len(env_path) > 0:
        dotenv.load_dotenv(dotenv_path=env_path, override=True)


def retrieve_metadata_records(metadata_submission_id: str) -> pd.DataFrame:
    env = dict(os.environ)
    response = requests.request(
        "GET",
        f"https://data.microbiomedata.org/api/metadata_submission/{metadata_submission_id}",
        cookies={"session": env["DATA_PORTAL_COOKIE"]},
    ).json()

    if "soil_data" in response["metadata_submission"]["sampleData"]:
        soil_data = response["metadata_submission"]["sampleData"]["soil_data"]
        df = pd.DataFrame(soil_data)

        return df
    else:
        raise ValueError(
            f"The soil data in submission metadata record: {metadata_submission_id} is empty."
        )


def combine_headers_df(json_mapper: dict) -> pd.DataFrame:
    d = {}
    for k, v in json_mapper.items():
        l = list()
        for h_n, h in v.items():
            if h_n != "sub_port_mapping":
                l.append(h)
        d[k] = l
    headers_df = pd.DataFrame(d)

    last_row = headers_df.iloc[-1]
    column_values = list(last_row)

    headers_df = headers_df.drop(headers_df.index[-1])
    headers_df.loc[len(headers_df)] = headers_df.columns.to_list()
    headers_df.columns = column_values

    shift = 1
    headers_df = pd.concat(
        [headers_df.iloc[-shift:], headers_df.iloc[:-shift]], ignore_index=True
    )

    return headers_df


def combine_sample_rows_df(df: pd.DataFrame, json_mapper: dict) -> pd.DataFrame:
    rows_df = pd.DataFrame()
    for _, v in json_mapper.items():
        if (
            "sub_port_mapping" in v
            and v["sub_port_mapping"] in df.columns.to_list()
            and "header" in v
        ):
            rows_df[v["header"]] = df[v["sub_port_mapping"]]
    return rows_df


def combine_headers_and_rows(
    headers_df: pd.DataFrame, rows_df: pd.DataFrame
) -> pd.DataFrame:
    return pd.concat([headers_df, rows_df])


@click.option("--submission", "-s", required=True, help="Metadata submission id.")
@click.option(
    "--mapper",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to user facility specific TSV file.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to result output XLSX file.",
)
@click.command()
def cli(submission, mapper, output):
    load_dotenv()
    metadata_submission = retrieve_metadata_records(submission)

    with open(mapper, "r") as f:
        json_mapper = json.load(f)

    headers_df = combine_headers_df(json_mapper)
    rows_df = combine_sample_rows_df(metadata_submission, json_mapper)
    user_facility_spreadsheet = combine_headers_and_rows(headers_df, rows_df)
    user_facility_spreadsheet.to_excel(output, index=False)


if __name__ == "__main__":
    cli()
