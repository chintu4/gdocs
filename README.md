# gdocs

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A lightweight, environment-agnostic Python package to seamlessly authenticate, read, and modify Google Docs. 

`gdocs` is designed to work flawlessly across different environments. It intelligently detects if you are running code inside **Google Colab** and uses native Colab authentication. If you are running locally or on a standard server, it gracefully falls back to local Application Default Credentials (ADC).

## ✨ Features

- **Environment Agnostic:** Works out-of-the-box in Google Colab, Jupyter Notebooks, and local Python scripts without code changes.
- **Recursive Parsing:** Automatically extracts text from standard paragraphs, complex nested tables, and lists.
- **Full Tabs Support:** Fully supports reading and navigating Google Docs' new nested Tabs structure.
- **AI-Ready Manipulation:** Built-in methods to append text, insert executive summaries, or replace template variables (ideal for LLM agent workflows).
- **Robust Error Handling:** Built-in isolated logging and graceful failure handling for API timeouts and HTTP errors.

## 📦 Installation

Since `gdocs` is currently in development and not yet published to PyPI, you can install it directly from the GitHub repository using standard `pip` or the faster `uv` package manager.

### Using pip
```bash
pip install git+[https://github.com/chintu4/gdocs.git](https://github.com/chintu4/gdocs.git)

```

### Using uv

```bash
uv pip install git+[https://github.com/chintu4/gdocs.git](https://github.com/chintu4/gdocs.git)

```

*(Note: This automatically installs required dependencies like `google-api-python-client` and `google-auth`)*

## 🔐 Authentication Setup

### 1. In Google Colab

**No setup required.** The package will automatically trigger the standard Colab authentication popup when you execute the client.

### 2. Local Environment

To run locally, you need to provide Google Cloud credentials via Application Default Credentials (ADC).

Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) and run:

```bash
gcloud auth application-default login

```

This opens a browser for you to sign in. `gdocs` will automatically detect and use these credentials.

## 🚀 Usage

### Basic Reading

Extract text from a full document, automatically parsing all tabs and nested tables:

```python
from gdocs.main import GoogleDocsService

# You can pass a full URL or just the ID directly!
DOCUMENT_URL = "[https://docs.google.com/document/d/1aBcD_eFgHiJkLmNoPqRsTuVwXyZ/edit](https://docs.google.com/document/d/1aBcD_eFgHiJkLmNoPqRsTuVwXyZ/edit)"

# Initialize the service (Handles auth automatically)
docs_service = GoogleDocsService()

# Read the entire document
text = docs_service.read_document(DOCUMENT_URL)
print(text)

```

### Working with Tabs

If your document utilizes Google Docs Tabs:

```python
# Get a dictionary mapping {tab_id: tab_title}
tabs = docs_service.get_tabs_info(DOCUMENT_URL)
print(tabs)

# Read a specific tab only
if tabs:
    first_tab_id = list(tabs.keys())[0]
    tab_text = docs_service.read_specific_tab(DOCUMENT_URL, target_tab_id=first_tab_id)

```

### Modifying Documents (AI Workflows)

Perfect for AI agents generating and logging content:

```python
# Append text to the very bottom of the document
docs_service.append_text(DOCUMENT_URL, text="\n\nAI Summary: This is an automated summary.")

# Insert text at the very beginning
docs_service.insert_text_at_start(DOCUMENT_URL, text="CONFIDENTIAL DRAFT\n")

# Replace template variables (e.g., replacing '{{NAME}}' with 'Alice')
docs_service.replace_text(DOCUMENT_URL, search_string="{{NAME}}", replacement_string="Alice")

```

## 📄 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).

```
