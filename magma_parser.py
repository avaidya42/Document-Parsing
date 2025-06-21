from parsing_utils import table_loader_multiple
import pandas as pd
import json
from utils import text_space_cleaner


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117161\RAPID ENGINEERING COMPANY PVT LIMITED_ GMC policy Copy 24-25.pdf"
# file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-9906-8604-2025-117114\GMC policy Copy 24-25.pdf"
file_path = "C:\Kare4U\document_parsing\other_documents\Magma HDI General Insurance\GHF-9906-8604-2025-115622\GHF-1501-8604-2025-115649\\08dd8efe-5f8a-4811-894d-bf57fb2c289a.pdf"

dfs = table_loader_multiple(file_path, "Policy Schedule /TAX INVOICE", "IN WITNESS WHEREOF")

next_df = False
for df in dfs:
    # print(df)
    cols = df.columns.tolist()
    if 'Policy Details' in cols:
        result = df.set_index(df.columns[0])[df.columns[1]].to_dict()
    elif "Cover" in cols and "Coverage Details" in cols:
        # print(df, cols)
        next_df = True
        result2 = {
            text_space_cleaner(key): value
            for key, value in zip(df.iloc[:, 0], df.iloc[:, 1])
            # if pd.notna(key) and pd.notna(value)
        }
        # continue
    elif next_df:
        next_df = False
        result3 = {cols[0]: cols[1]}
        result3.update({
            text_space_cleaner(key): value
            for key, value in zip(df.iloc[:, 0], df.iloc[:, 1])
            # if pd.notna(key) and pd.notna(value)
        })

print(json.dumps(result, indent=4))
print(json.dumps(result2, indent=4))
print(json.dumps(result3, indent=4))

