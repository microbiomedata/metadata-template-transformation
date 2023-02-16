import pandas as pd
import csv
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


def retrieve_metadata_records(metadata_submission_id: str = None):
    env = dict(os.environ)
    if metadata_submission_id:
        response = requests.request(
            "GET",
            f"https://data.microbiomedata.org/api/metadata_submission/{metadata_submission_id}",
            cookies={"session": env["DATA_PORTAL_COOKIE"]},
        ).json()
    else:
        response = requests.request(
            "GET",
            "https://data.microbiomedata.org/api/metadata_submission/",
            cookies={"session": env["DATA_PORTAL_COOKIE"]},
        ).json()["results"]

    if isinstance(response, dict):
        if "sampleData" in response:
            table = response["sampleData"]
            if table and len(table) > 2:
                df = pd.DataFrame(table[2:], columns=table[1])
                return df
    elif isinstance(response, list):
        metadata_dfs = []
        for metadata in response:
            for _, metadata_submission_v in metadata.items():
                if isinstance(metadata_submission_v, dict):
                    if "sampleData" in metadata_submission_v:
                        table = metadata_submission_v["sampleData"]
                        if table and len(table) > 2:
                            df = pd.DataFrame(table[2:], columns=table[1])
                            metadata_dfs.append(df)

        return metadata_dfs


def user_facility_config_dict(user_facility_config_path):
    user_facility_sub_port = {}
    with open(user_facility_config_path, newline="\n") as csv_f:
        for row in csv.DictReader(csv_f, delimiter="\t"):
            user_facility_sub_port[row["user_facility_field"]] = row["sub_port_field"]

    return user_facility_sub_port


def user_facility_sub_port_etl(user_facility_sub_port, sub_port_df, user_facility_dict):
    user_facility_dict_new_values = {}

    for user_facility_header, user_facility_row in user_facility_dict.items():
        if user_facility_sub_port[user_facility_header]:
            user_facility_row = user_facility_dict[user_facility_header]

            if user_facility_sub_port[user_facility_header] in sub_port_df:
                sub_port_dict = sub_port_df[
                    user_facility_sub_port[user_facility_header]
                ].to_dict()

            if user_facility_row:
                if "header" in user_facility_row:
                    del user_facility_row["header"]

                key_max_cnt = int(max(user_facility_row, key=int)) + int(1)
            else:
                key_max_cnt = 0
            for sub_port_header, sub_port_values in sub_port_dict.items():
                user_facility_row[key_max_cnt + sub_port_header] = sub_port_values
            user_facility_dict_new_values[user_facility_header] = user_facility_row

    return user_facility_dict_new_values


def user_facility_sub_port_df(user_facility_dict):
    user_facility_sub_port_merged_df = pd.DataFrame(user_facility_dict)
    user_facility_sub_port_merged_df = (
        user_facility_sub_port_merged_df.T.reset_index().T.reset_index(drop=True)
    )

    return user_facility_sub_port_merged_df


@click.option("--submission", "-s", help="Metadata submission id.")
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Path to submission portal TSV export.",
)
@click.option(
    "--header", "-h", help="Path to user facility template headers JSON file."
)
@click.option(
    "--mapper",
    "-m",
    type=click.Path(exists=True),
    help="Path to user facility specific TSV file.",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Path to result output XLSX file."
)
@click.command()
def cli(submission, input, header, mapper, output):
    """Convert submission portal metadata to a DOE user facility specific format."""
    load_dotenv()

    if submission:
        sub_port_df = retrieve_metadata_records(submission)
    elif input:
        sub_port_df = pd.read_csv(input, delimiter="\t", header=1)
    else:
        raise ValueError("Either --submission or --input arguments must be provided.")

    user_facility_sub_port = user_facility_config_dict(mapper)

    with open(header, encoding="utf-8") as f:
        user_facility_dict = json.load(f)

    user_facility_cols = []
    for _, v in user_facility_dict.items():
        if "header" in v:
            user_facility_cols.append(v["header"])
        else:
            user_facility_cols.append("")

    user_facility_sub_port_updated = user_facility_sub_port_etl(
        user_facility_sub_port, sub_port_df, user_facility_dict
    )

    for _, v in user_facility_dict.items():
        if "header" in v:
            del v["header"]

    user_facility_dict.update(user_facility_sub_port_updated)

    user_facility_sub_port_merged_df = user_facility_sub_port_df(user_facility_dict)

    user_facility_sub_port_merged_df.columns = user_facility_cols

    user_facility_sub_port_merged_df.to_excel(output, index=False)


if __name__ == "__main__":
    cli()
