import sys
from reliance_module import parse_reliance_pdf  # Or your correct import
import json

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf>")
        return

    pdf_path = sys.argv[1]
    result = parse_reliance_pdf(pdf_path)

    # Save output to file
    with open("output.json", "w") as f:
        json.dump(result, f, indent=2)

    print("✅ Output saved to output.json")

if __name__ == "__main__":
    main()
