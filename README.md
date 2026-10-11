# gdocs

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/gdocs)](https://pypi.org/project/gdocs/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

A lightweight, environment-agnostic Python package designed to read, parse, and modify Google Docs with minimal boilerplate.

`gdocs` automatically adapts to your runtime environment:

- **Google Colab:** Uses Colab's native authentication flow.
- **Local PC / Servers:** Automatically detects and uses Google Cloud Application Default Credentials (ADC).
- **Automated workflows:** Supports service account authentication for server-side applications and CI/CD pipelines.

---

## 💡 Why `gdocs`?

Working directly with the Google Docs API using `google-api-python-client` typically requires significant boilerplate for authentication, document retrieval, and content parsing.

`gdocs` streamlines the workflow with a clean, developer-friendly API.

| Feature | Raw Google Docs API | With `gdocs` |
|---|---|---|
| Authentication | Manual credential setup and token management | Automatic environment-aware authentication |
| Document IDs | Manually extract IDs from URLs | Accepts full URLs or document IDs |
| Reading text | Traverse nested API response objects | `docs.read_document(url)` |
| Tables and tabs | Implement custom recursive parsing | Built-in recursive parsing and tab navigation |
| Document editing | Construct `batchUpdate` request payloads | Helper methods such as `append_text()` and `replace_text()` |

---

## ✨ Features

- **Simple imports:** Import `GoogleDocsService` directly from `gdocs`.
- **Environment agnostic:** Work across Google Colab, local machines, and servers.
- **Recursive parsing:** Extract text from paragraphs, lists, and nested tables.
- **Google Docs tabs support:** Retrieve tab information and read specific tabs.
- **Document modification:** Append text, insert content at the beginning, and replace text.
- **AI-ready workflows:** Integrate document operations into LLM applications and automation pipelines.
- **Extensible authentication:** Use the `AuthStrategy` architecture to customize authentication.

---

## 📦 Installation

`gdocs` is published on PyPI and can be installed using either `uv` or `pip`.

### Using uv (Recommended)

```bash
uv pip install gdocs
```

For projects managed with `uv`, you can also add it as a dependency:

```bash
uv add gdocs
```

### Using pip

```bash
pip install gdocs
```

### Verify the installation

```python
from gdocs import GoogleDocsService

print("gdocs installed successfully!")
```

---

## 🔐 Authentication Guide

Before using the package, ensure that the Google Docs API is enabled in your Google Cloud project and that your credentials have access to the target document.

### 1. Google Colab

Google Colab supports interactive authentication through its native authentication flow.

#### Method A: Automatic Colab authentication

```python
from gdocs import GoogleDocsService

# Uses the package's Colab authentication flow
docs = GoogleDocsService()
```

If you prefer to authenticate explicitly beforehand:

```python
from google.colab import auth

auth.authenticate_user()

from gdocs import GoogleDocsService

docs = GoogleDocsService()
```

#### Method B: Service account authentication

For service-account-based workflows, configure the credentials file:

```python
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "/content/service_account.json"
)

from gdocs import GoogleDocsService

docs = GoogleDocsService()
```

Ensure the service account has access to the document.

### 2. Local PC: Windows, macOS, and Linux

#### Method A: Application Default Credentials (ADC)

ADC is recommended for local development, scripts, and Jupyter notebooks.

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
2. Enable the Google Docs API and configure your Google Cloud project.
3. Authenticate using the following command:

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/drive.readonly
```

4. Complete the browser authentication flow.
5. Initialize the service:

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()
```

The credentials are stored locally and discovered through Google's ADC mechanism.

**Note:** The scopes above provide Google Docs access and read-only Google Drive access. Configure any additional permissions required by your workflow.

#### Method B: Service account JSON file

Service accounts are useful for servers, background workers, Docker containers, and CI/CD pipelines.

1. Create a service account in the [Google Cloud Console](https://console.cloud.google.com/).
2. Configure the required permissions and obtain the JSON credentials file if your environment uses key-based authentication.
3. Share the target Google Doc with the service account's email address, granting Viewer or Editor access as appropriate.
4. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.

**Linux / macOS:**

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"
```

**Windows PowerShell:**

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service_account.json"
```

5. Initialize the service:

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()
```

For production environments, prefer secure credential management or workload identity where supported instead of committing service account keys to your repository.

---

## 🚀 Usage Guide

### 1. Read a Google Doc

Pass either the complete Google Docs URL or the document ID.

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()

DOC_URL = (
    "https://docs.google.com/document/d/"
    "YOUR_DOCUMENT_ID/edit"
)

# Read and extract document text
content = docs.read_document(DOC_URL)

print(content)
```

The package provides a convenient interface for extracting text from supported document content, including paragraphs, lists, and nested tables.

### 2. Work with Google Docs tabs

For documents containing multiple tabs, retrieve the available tab IDs and titles before reading a specific tab.

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()

DOC_URL = (
    "https://docs.google.com/document/d/"
    "YOUR_DOCUMENT_ID/edit"
)

# Retrieve available tabs
tabs = docs.get_tabs_info(DOC_URL)

print("Available tabs:", tabs)

# Read the first available tab
if tabs:
    first_tab_id = next(iter(tabs))

    tab_content = docs.read_specific_tab(
        DOC_URL,
        target_tab_id=first_tab_id,
    )

    print(tab_content)
```

### 3. Modify a Google Doc

Use the built-in helper methods for common document-editing tasks.

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()

DOC_URL = (
    "https://docs.google.com/document/d/"
    "YOUR_DOCUMENT_ID/edit"
)

# Append text to the end of the document
docs.append_text(
    DOC_URL,
    text="\n\nAI Summary\nDocument processing completed successfully.",
)

# Insert text at the beginning of the document
docs.insert_text_at_start(
    DOC_URL,
    text="CONFIDENTIAL DRAFT - FOR INTERNAL USE ONLY\n\n",
)

# Replace template placeholders
docs.replace_text(
    DOC_URL,
    search_string="{{CLIENT_NAME}}",
    replacement_string="Acme Corporation",
)
```

**Important:** These operations modify the actual Google Doc. Ensure that your credentials have editing permission and that you intend to apply the changes.

### 4. Use a custom authentication strategy

For applications that need explicit control over authentication, you can provide an authentication strategy.

```python
from gdocs import DefaultAuthStrategy, GoogleDocsService

auth = DefaultAuthStrategy()

docs = GoogleDocsService(
    auth_strategy=auth,
)
```

The available authentication strategies and their behavior depend on the package implementation.

---

## 🤖 Use with AI and LLM Workflows

`gdocs` can serve as a lightweight integration layer between Google Docs and AI applications.

A typical workflow:

1. Read a Google Doc using `read_document()`.
2. Pass the extracted content to your LLM or text-processing pipeline.
3. Generate a summary or transform the document content.
4. Write the generated content back using the supported editing methods.

Example:

```python
from gdocs import GoogleDocsService

docs = GoogleDocsService()

DOC_URL = (
    "https://docs.google.com/document/d/"
    "YOUR_DOCUMENT_ID/edit"
)

document_text = docs.read_document(DOC_URL)

# Pass document_text to your preferred LLM or processing pipeline.
# Generate your summary here.

summary = "Your generated summary goes here."

docs.append_text(
    DOC_URL,
    text=f"\n\nAI Summary\n{summary}",
)
```

The LLM integration is left to your application, allowing you to use your preferred provider or local model.

---

## 🛠️ Local Development and Contributing

Contributions, bug reports, and feature suggestions are welcome.

### Clone the repository

```bash
git clone https://github.com/chintu4/gdocs.git

cd gdocs
```

### Create a virtual environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv .venv

source .venv/bin/activate
```

### Install in editable mode

Using `uv`:

```bash
uv pip install -e .
```

Alternatively, using pip:

```bash
pip install -e .
```

Editable installation allows local source changes to be reflected without reinstalling the package, subject to the project's packaging configuration.

### Develop in Google Colab

```python
!git clone https://github.com/chintu4/gdocs.git
%pip install -e ./gdocs
```

Enable autoreload when working interactively:

```python
%load_ext autoreload
%autoreload 2

from gdocs import GoogleDocsService
```

---

## 🔗 Links

- **PyPI:** https://pypi.org/project/gdocs/
- **GitHub Repository:** https://github.com/chintu4/gdocs
- **Google Docs API:** https://developers.google.com/workspace/docs/api
- **Google Cloud CLI:** https://cloud.google.com/sdk/docs/install

---

## 📄 License

This project is licensed under the MIT License. See the repository's `LICENSE` file for details.
````
