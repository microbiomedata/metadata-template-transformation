import pandas as pd
import csv
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

SUB_PORT_FILE_PATH = "example-files/SoilExample_nmdc_sample_export.tsv"
EMSL_FILE_PATH = "example-files/EMSL_Metadata_Example.xlsm"
EMSL_SHEET_NAME = "Samples"
EMSL_CONFIG = "mapping-configs/emsl.tsv"

def emsl_config_dict(emsl_config_path):
    emsl_sub_port = {}
    with open(emsl_config_path, newline="\n") as csv_f:
        for row in csv.DictReader(csv_f, delimiter="\t"):
            emsl_sub_port[row["emsl_field"]] = row["sub_port_field"]

    return emsl_sub_port

def emsl_sub_port_etl(emsl_dict):
    emsl_dict_new_values = {}

    for emsl_header, emsl_row in emsl_dict.items():
        if emsl_sub_port[emsl_header]:
            emsl_row = emsl_dict[emsl_header]
            sub_port_dict = sub_port_df[emsl_sub_port[emsl_header]].to_dict()
            key_max_cnt = max(emsl_row, key=int) + 1
            for sub_port_header, sub_port_values in sub_port_dict.items():
                emsl_row[key_max_cnt + sub_port_header] = sub_port_values
            emsl_dict_new_values[emsl_header] = emsl_row

    return emsl_dict_new_values

def emsl_sub_port_df(emsl_dict):
    emsl_sub_port_merged_df = pd.DataFrame(emsl_dict)
    emsl_sub_port_merged_df = emsl_sub_port_merged_df.T.reset_index().T.reset_index(drop=True)

    return emsl_sub_port_merged_df

if __name__ == "__main__":
    sub_port_df = pd.read_csv(SUB_PORT_FILE_PATH, delimiter="\t", header=1)

    emsl_df = pd.read_excel(EMSL_FILE_PATH, sheet_name=EMSL_SHEET_NAME)

    emsl_cols = emsl_df.columns

    emsl_df = emsl_df.rename(columns=emsl_df.iloc[0]).drop(emsl_df.index[0])

    emsl_sub_port = emsl_config_dict(EMSL_CONFIG)

    emsl_dict = emsl_df.to_dict()

    emsl_sub_port_updated = emsl_sub_port_etl(emsl_dict)
    
    emsl_dict.update(emsl_sub_port_updated)

    emsl_sub_port_merged_df = emsl_sub_port_df(emsl_dict)

    emsl_sub_port_merged_df.columns = emsl_cols

    emsl_sub_port_merged_df.to_excel("result.xlsx", index=False)
