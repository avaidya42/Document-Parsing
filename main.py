import sys
import json
import ast
from reliance_module import parse_reliance_pdf  # Make sure this returns a dict, not a string

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf>")
        return

    pdf_path = sys.argv[1]
    result = parse_reliance_pdf(pdf_path)

    # Safety: convert string dict to real dict if needed
    if isinstance(result, str):
        try:
            result = ast.literal_eval(result)
        except Exception as e:
            print("❌ Error converting string to dict:", e)
            return

    # Save output to JSON file
    with open("output.json", "w") as f:
        json.dump(result, f, indent=4)

    print("✅ Output saved to output.json")

if __name__ == "__main__":
    main()
