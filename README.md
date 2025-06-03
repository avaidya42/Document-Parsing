# Insurance PDF Parser

## Overview
This project is a tool for parsing insurance policy documents (PDFs) to extract structured information about coverage details, and policy terms.

## Features
- Extracts text and coordinates from PDF documents
- Identifies and extracts information based on headings
- Processes policy details including:
- The exact structure of the desired output data can be found under `utils.py`

## Guidelines
- Run `main.py` to see the output for the files under `coverage_documents`.

## Tasks
- Choose a folder under `other_documents`
- Go through files to familiarize with the format.
- Check `utils.py` for desired output fields and divide the contents into parts that can be manually parsed and those that need LLM assistance
- Write/modify functions to parse the documents to obtain the information in these two categories, and pass the latter to an LLM for conversion to a structured format.


## Project Structure
- `app_cpu.py` - FastAPI endpoint for the process
- `main.py` - Main parsing function and entry point
- `parsing_utils.py` - Utilities for manually extracting text and data from PDFs
- `prompt_utils.py` - Utilities for generating and handling LLM prompts
- `utils.py` - General utility functions


## Output
The parser outputs structured JSON data containing extracted policy information, which can be used for further analysis or integration with other systems.


