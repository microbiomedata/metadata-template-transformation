import pandas as pd
import os
import json
import click
import dotenv
import requests


def load_dotenv():
    env_path = dotenv.find_dotenv()
    if len(env_path) > 0:
        dotenv.load_dotenv(dotenv_path=env_path, override=True)


def retrieve_metadata_records(
    user_facility, metadata_submission_id: str
) -> pd.DataFrame:
    env = dict(os.environ)
    response = requests.request(
        "GET",
        f"https://data.microbiomedata.org/api/metadata_submission/{metadata_submission_id}",
        cookies={"session": env["DATA_PORTAL_COOKIE"]},
    ).json()

    if user_facility == "emsl":
        if "soil_data" in response["metadata_submission"]["sampleData"]:
            soil_data = response["metadata_submission"]["sampleData"]["soil_data"]
            soil_data_df = pd.DataFrame(soil_data)

        if "emsl_data" in response["metadata_submission"]["sampleData"]:
            emsl_data = response["metadata_submission"]["sampleData"]["emsl_data"]
            emsl_data_df = pd.DataFrame(emsl_data)

        df = pd.DataFrame()
        if soil_data_df.empty and not emsl_data_df.empty:
            df = emsl_data_df
        elif emsl_data_df.empty and not soil_data_df.empty:
            df = soil_data_df
        elif not emsl_data_df.empty and not soil_data_df.empty:
            common_cols = list(
                set(emsl_data_df.columns.to_list())
                & set(soil_data_df.columns.to_list())
            )
            if "source_mat_id" in common_cols:
                common_cols.remove("source_mat_id")

            emsl_data_df = emsl_data_df.drop(columns=common_cols)
            df = pd.merge(soil_data_df, emsl_data_df, on="source_mat_id")
            print(df.columns.to_list())
        else:
            raise ValueError(
                f"The submission metadata record: {metadata_submission_id} is empty."
            )

        return df


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


def combine_sample_rows_df(
    submission_df: pd.DataFrame, json_mapper: dict
) -> pd.DataFrame:
    rows_df = pd.DataFrame()
    for _, v in json_mapper.items():
        if (
            "sub_port_mapping" in v
            and v["sub_port_mapping"] in submission_df.columns.to_list()
            and "header" in v
        ):
            rows_df[v["header"]] = submission_df[v["sub_port_mapping"]]

    return rows_df


def combine_headers_and_rows(
    headers_df: pd.DataFrame, rows_df: pd.DataFrame
) -> pd.DataFrame:
    return pd.concat([headers_df, rows_df])


@click.option("--submission", "-s", required=True, help="Metadata submission id.")
@click.option(
    "--user-facility", "-u", required=True, help="User facility to send data to."
)
@click.option(
    "--mapper",
    "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to user facility specific JSON file.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to result output XLSX file.",
)
@click.command()
def cli(submission, user_facility, mapper, output):
    load_dotenv()
    metadata_submission = retrieve_metadata_records(user_facility, submission)

    with open(mapper, "r") as f:
        json_mapper = json.load(f)

    headers_df = combine_headers_df(json_mapper)
    rows_df = combine_sample_rows_df(metadata_submission, json_mapper)
    user_facility_spreadsheet = combine_headers_and_rows(headers_df, rows_df)
    user_facility_spreadsheet.to_excel(output, index=False)


if __name__ == "__main__":
    cli()
