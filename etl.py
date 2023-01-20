import pandas as pd
import csv
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

sub_port_df = pd.read_csv(
    "example-files/SoilExample_nmdc_sample_export.tsv", delimiter="\t", header=1
)

emsl_df = pd.read_excel(
    "example-files/EMSL_Metadata_Example.xlsm", sheet_name="Samples"
)

emsl_cols = emsl_df.columns

emsl_df = emsl_df.rename(columns=emsl_df.iloc[0]).drop(emsl_df.index[0])

emsl_sub_port = {}
with open("mapping-configs/emsl.tsv", newline="\n") as csv_f:
    for row in csv.DictReader(csv_f, delimiter="\t"):
        emsl_sub_port[row["emsl_field"]] = row["sub_port_field"]

sub_port_cols = [val for val in list(emsl_sub_port.values()) if val]

emsl_dict = emsl_df.to_dict()
emsl_dict_new_values = {}

for emsl_header, emsl_row in emsl_df.to_dict().items():
    if emsl_sub_port[emsl_header]:
        emsl_row = emsl_dict[emsl_header]
        sub_port_dict = sub_port_df[emsl_sub_port[emsl_header]].to_dict()
        key_max_cnt = max(emsl_row, key=int) + 1
        for sub_port_header, sub_port_values in sub_port_dict.items():
            emsl_row[key_max_cnt + sub_port_header] = sub_port_values
        emsl_dict_new_values[emsl_header] = emsl_row

emsl_dict.update(emsl_dict_new_values)

emsl_sub_port_merged_df = pd.DataFrame(emsl_dict)
emsl_sub_port_merged_df = emsl_sub_port_merged_df.T.reset_index().T.reset_index(drop=True)

emsl_sub_port_merged_df.columns = emsl_cols
emsl_sub_port_merged_df.to_excel("result.xlsx", index=False)