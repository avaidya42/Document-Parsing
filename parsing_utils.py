from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from typing import Dict
import re
import tabula
import pandas as pd
import json
# from prompt_utils import prompt_field
from utils import text_space_cleaner
import fitz


def get_headings():
    actual_headings = ["Policy Number", "Risk Inception Date", "Floater Details", "Outpatient Details",
                       "Risk Expiry Date",
                       "HAT Reference Number", "Policy Active With other Insured", "Policy Active With Bajaj Allianz",
                       "Beneficiary Name", "Pre Hospitalization Period[Days]", "Post Hospitalization Period[Days]",
                       "Corporate A/C No", "Maternity Benefit", "Limit for no of Children", "Max for LSCS",
                       "Corporate Buffer Amount", "Room Restrictions", "Max liability on maternity exp",
                       "Co-payment for maternity", "Corporate Buffer", "9 Months waiting period",
                       "Max for normal delivery",
                       "Per Family Maximum"]
    return actual_headings


def extract_text_with_coordinates(pdf_path) -> Dict:
    text_with_coords = {}
    for page_layout in extract_pages(pdf_path):
        page_number = page_layout.pageid - 1  # pageid starts at 1
        text_with_coords[page_number] = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                bbox = element.bbox  # (x0, y0, x1, y1)
                text = text_space_cleaner(element.get_text())
                # text = element.get_text()
                # text = re.sub(r'-\n', '', element.get_text())
                # text = re.sub(r'\n', ' ', text)
                if text:
                    text_with_coords[page_number].append({"text": text.strip(), "bbox": bbox})
    # print(text_with_coords)
    return text_with_coords


def find_heading_coordinates(text_with_coords, headings) -> Dict:
    heading_coords = {}
    # print(len(text_with_coords))
    for i in range(max(text_with_coords.keys()) + 1):
        for item in text_with_coords[i]:
            for heading in headings:
                # if heading == "Maternity Benefit":
                #     heading = "Maternity Benifit"
                if heading.lower() == item["text"].lower():
                    heading_coords[heading] = [i, item["bbox"]]
                    headings.remove(heading)
                    # heading_coords["page"] = i
                    break
                elif heading == "Maternity Benefit":
                    if item["text"].lower() == "maternity benifit":
                        heading_coords[heading] = [i, item["bbox"]]
                        headings.remove(heading)
                # insert if condition to check for incorrect spelling and replace with
                # correct spelling in the heading list
        if len(heading_coords) == len(headings):
            break
    # print(len(heading_coords))
    return heading_coords


def extract_text_near_heading(text_with_coords, headings, heading_coords, offset=50, yoffset=5) -> Dict:
    # print(headings)
    extracted_data = {}
    for heading, bbox in heading_coords.items():
        page = bbox[0]
        x0, y0, x1, y1 = bbox[1]
        leftmost_text = None
        leftmost_x0 = float('inf')

        for item in text_with_coords[page]:
            ix0, iy0, ix1, iy1 = item["bbox"]
            # Check if the text is within a certain distance near the heading
            # if ix0 > x1 and ix0 <= x1 + 3 * (x1 - x0) and iy1 >= y1 - yoffset and iy1 <= y1 + yoffset:
            if x1 < ix0 <= x1 + 3 * (x1 - x0) and y1 - yoffset <= iy1 <= y1 + yoffset:
                # Check if this is the leftmost box encountered
                if ix0 < leftmost_x0:
                    leftmost_x0 = ix0
                    leftmost_text = item["text"]

        if leftmost_text and leftmost_text not in headings:
            # print(f"-{leftmost_text}-")
            extracted_data[heading] = leftmost_text.strip()
        else:
            extracted_data[heading] = ""

    return extracted_data


def get_tables(pdf_path):
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    # for df in dfs:
    #     print(df)
    return dfs


def output(llm_out):
    text = ""
    for key, value in llm_out.items():
        text += key + "\n"
        for key2, value2, in value.items():
            text += "\t" + key2 + ": " + str(value2)
            text += "\n"
        text += "\n"
    # print(text)
    with open("output_layout.txt", "w") as f:
        f.write(text)


def main():
    # actual_headings = ["Policy Number", "Risk Inception Date", "Floater Details", "Outpatient Details",
    #                    "Risk Expiry Date",
    #                    "HAT Reference Number", "Policy Active With other Insured", "Policy Active With Bajaj Allianz",
    #                    "Beneficiary Name", "Pre Hospitalization Period[Days]", "Post Hospitalization Period[Days]",
    #                    "Corporate A/C No", "Maternity Benefit", "Limit for no of Children", "Max for LSCS",
    #                    "Corporate Buffer Amount", "Room Restrictions", "Max liability on maternity exp",
    #                    "Co-payment for maternity",
    #                    "Corporate Buffer", "9 Months waiting period", "Max for normal delivery", "Per Family Maximum"]
    actual_headings = get_headings()
    # for i in range(10):
    # i = 1
    pdf_path = f"C:\\Kare4U\\policyParsing\\coverage_documents\\Benefit Chart.pdf"
    text_with_coords = extract_text_with_coordinates(pdf_path)
    # print(text_with_coords)
    heading_coords = find_heading_coordinates(text_with_coords, actual_headings)
    # print(heading_coords)
    actual_headings = get_headings()
    extracted_data = extract_text_near_heading(text_with_coords, actual_headings, heading_coords)
    print(extracted_data)
    # for heading, data in extracted_data.items():
    #     print(f"{heading}: {data}")

    # get_tables(pdf_path)


# def pdf_parser(pdf_path):
#     actual_headings = get_headings()
#     text_with_coords = extract_text_with_coordinates(pdf_path)
#     unstructured_text = ""
#     con = False
#     con2 = False
#     for i in range(max(text_with_coords.keys()) + 1):
#         for item in text_with_coords[i]:
#             if not con:
#                 if "claim conditions" == item['text'].lower():
#                     con = True
#                     unstructured_text += item['text'] + "\n"
#             else:
#                 if "quote disclaim" in item['text'].lower():
#                     # con2 = True
#                     # break
#                     pass
#                 unstructured_text += item['text'] + "\n"
#         if con2:
#             break
#
#     heading_coords = find_heading_coordinates(text_with_coords, actual_headings)
#     extracted_data = extract_text_near_heading(text_with_coords, actual_headings, heading_coords)
#
#     result = {}
#     for heading, data in extracted_data.items():
#         result[heading] = data
#
#     maternity_expense = result["Max liability on maternity exp"]
#     room_restrictions = result["Room Restrictions"]
#     llm_out = eval(prompt_field(unstructured_text, maternity_expense, room_restrictions))
#
#     llm_out["maternity_expenses"]["limit_normal_delivery"] = result["Max for normal delivery"]
#     llm_out["maternity_expenses"]["limit_c_section"] = result["Max for LSCS"]
#     if "not" in result["9 Months waiting period"].lower():
#         llm_out["maternity_expenses"]["waiting_period"] = "No waiting period"
#     else:
#         llm_out["maternity_expenses"]["waiting_period"] = "9 Months waiting period"
#     llm_out["pre_hospitalization"] = {"pre_hospitalization_period": result["Pre Hospitalization Period[Days]"]}
#     llm_out["post_hospitalization"] = {"post_hospitalization_period": result["Post Hospitalization Period[Days]"]}
#
#     llm_out = llm_out | {"headings": result}
#     output(llm_out)
#     with open('llm_result.json', 'w') as f3:
#         json.dump(llm_out, f3, indent=4)
#     return llm_out


def table_loader(file_path, pdf_docs):
    doc = fitz.open(file_path)
    counter = 0
    for page in doc:
        tabs = page.find_tables()
        for tab in tabs:
            # print(tab.to_pandas())
            pdf_docs += (tab.to_pandas()).to_string(index=False, na_rep='') + '\n\n'
        counter += 1
        if counter >= 5:
            break
    return pdf_docs


def table_loader_first(file_path):
    doc = fitz.open(file_path)
    for page in doc:
        tabs = page.find_tables()
        for tab in tabs:
            df = tab.to_pandas()
            # print(df)
            df.columns = [re.sub(r'-\n', '', re.sub(r'\n', ' ', col)) for col in df.columns]
            # print(df.columns)
            if "Pre-Existing Diseases" in df.columns:
                df = df.map(text_space_cleaner)
                # print(df)
                return df


def table_loader_csv(file_path, pdf_docs):
    doc = fitz.open(file_path)
    counter = 0
    for page in doc:
        tabs = page.find_tables()
        for tab in tabs:
            # print(tab.to_pandas())
            pdf_docs += (tab.to_pandas()).to_csv() + '\n\n'
            # pdf_docs += (tab.to_pandas()).to_json()
        counter += 1
        if counter >= 5:
            break
    return pdf_docs


def all_loader(file_path):
    pdf_docs = ""
    doc = fitz.open(file_path)
    for page_num in range(min(5, doc.page_count)):
        page = doc.load_page(page_num)
        pdf_docs += page.get_text("text")
    return pdf_docs


if __name__ == '__main__':
    main()
