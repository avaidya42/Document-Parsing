from parsing_utils import table_loader_multiple
import pandas as pd
import json
from utils import text_space_cleaner
from collections import Counter


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117161\RAPID ENGINEERING COMPANY PVT LIMITED_ GMC policy Copy 24-25.pdf"
# file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117114\GMC policy Copy 24-25.pdf"
file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-1501-8604-2025-115649\\08dd8efe-5f8a-4811-894d-bf57fb2c289a.pdf"

dfs = table_loader_multiple(file_path, "Policy Schedule /TAX INVOICE", "IN WITNESS WHEREOF")

def convert_to_dict(df, result, key_counts, include_headers=False):
    def repeat_checker(key_counts, key):
        if key_counts[key] > 1:
            final_key = f"{key}_{key_counts[key]}"
        else:
            final_key = key
        return final_key

    if include_headers:
        cols = df.columns.tolist()
        if len(cols) >= 2:
            header_key = text_space_cleaner(cols[0])
            key_counts[header_key] += 1

            result[repeat_checker(key_counts, header_key)] = cols[1]

    for key, value in zip(df.iloc[:, 0], df.iloc[:, 1]):
        if pd.notna(key) and pd.notna(value):
            cleaned_key = text_space_cleaner(key)
            key_counts[cleaned_key] += 1

            # Add number suffix for duplicates

            result[repeat_checker(key_counts, cleaned_key)] = value
    # return result

key_counts = Counter()
result = {}

next_df = False
for df in dfs:
    # print(df)
    cols = df.columns.tolist()
    if 'Policy Details' in cols:
        extra_result = df.set_index(df.columns[0])[df.columns[1]].to_dict()
    elif "Cover" in cols and "Coverage Details" in cols:
        # print(df, cols)
        next_df = True
        convert_to_dict(df, result, key_counts)
        # continue
    elif next_df:
        next_df = False
        convert_to_dict(df, result, key_counts, include_headers=True)

print(json.dumps(result, indent=4))
print(json.dumps(extra_result, indent=4))

