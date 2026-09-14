
# gdocs

A lightweight Python package to seamlessly authenticate and extract text from Google Docs. 

`gdocs` is designed to work flawlessly across different environments. It intelligently detects if you are running code inside **Google Colab** and uses the native Colab authentication. If you are running locally or on a standard server, it gracefully falls back to local Application Default Credentials (ADC).

## Features

- **Environment Agnostic:** Works out-of-the-box in Google Colab, Jupyter Notebooks, and local Python scripts.
- **Recursive Parsing:** Automatically extracts text from standard paragraphs, complex tables, and lists.
- **Robust Error Handling:** Built-in logging and graceful failure handling for API timeouts and HTTP errors.
- **Smart ID Extraction:** Pass either a full Google Docs URL or just the Document ID.

## Installation

Since `gdocs` is not yet published to PyPI, you can install it directly from the GitHub repository. You can use standard `pip` or the faster `uv` package manager.

### Using pip
```bash
pip install git+[https://github.com/chintu4/gdocs.git](https://github.com/chintu4/gdocs.git)

```

### Using uv

```bash
uv pip install git+[https://github.com/chintu4/gdocs.git](https://github.com/chintu4/gdocs.git)

```

*(Note: This will automatically install the required dependencies like `google-api-python-client` and `google-auth` as defined in your `pyproject.toml`)*

## Authentication Setup

### 1. In Google Colab

No setup is required. The package will automatically trigger the standard Colab authentication popup when you run your code.

### 2. Local Environment

If you are running this locally, you need to provide Google Cloud credentials. The easiest way is using Application Default Credentials (ADC).

Install the Google Cloud CLI and run:

```bash
gcloud auth application-default login

```

This will open a browser to sign in, and `gdocs` will automatically detect these credentials.

## Usage

Here is a quick example of how to extract text from a document:

```python
import os
from gdocs.main import GoogleDocsService, extract_doc_id

# You can pass a full URL or just the ID
DOCUMENT_URL = "[https://docs.google.com/document/d/1aBcD_eFgHiJkLmNoPqRsTuVwXyZ/edit](https://docs.google.com/document/d/1aBcD_eFgHiJkLmNoPqRsTuVwXyZ/edit)"

# Extract the ID from the URL
doc_id = extract_doc_id(DOCUMENT_URL)

# Initialize the service (Handles auth automatically)
docs_service = GoogleDocsService()

# Read the document
extracted_text = docs_service.read_document(doc_id)

if extracted_text:
    print("--- Document Content ---")
    print(extracted_text)
else:
    print("Document is empty or could not be read.")

```

## License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).

```
