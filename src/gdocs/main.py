import re
import logging
import os
from typing import Optional

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure standard logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)

class GoogleDocsService:
    """
    A unified service class to handle Google Docs authentication and parsing.
    Dynamically adapts to run inside Google Colab or on a local machine.
    """
    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy initialization of the Google Docs API client."""
        if self._client is None:
            self._client = self._authenticate_and_build()
        return self._client

    def _authenticate_and_build(self):
        """Authenticates using Colab if available, otherwise falls back to local credentials."""
        try:
            # Strategy 1: Google Colab Environment
            from google.colab import auth
            auth.authenticate_user()
            creds, _ = google.auth.default()
            logging.info("Authenticated using Google Colab environment.")
            
        except ImportError:
            # Strategy 2: Local Environment (Application Default Credentials)
            # Ensure you have run `gcloud auth application-default login` locally
            creds, _ = google.auth.default()
            logging.info("Authenticated using local Application Default Credentials.")
        
        try:
            return build('docs', 'v1', credentials=creds)
        except HttpError as e:
            raise RuntimeError(f"Failed to build Google Docs service: {e}")

    def read_document(self, document_id: str) -> Optional[str]:
        try:
            document = self.client.documents().get(documentId=document_id).execute()
            return self._extract_text(document.get('body', {}).get('content', []))
        except HttpError as err:
            logging.error(f"Google API Error: {err.status_code} - {err.reason}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None

    def _extract_text(self, elements: list) -> str:
        """
        Recursively parses structural elements (paragraphs, tables, lists) to extract text.
        """
        text = ""
        for element in elements:
            if 'paragraph' in element:
                for p_elem in element.get('paragraph', {}).get('elements', []):
                    text_run = p_elem.get('textRun', {})
                    if text_run:
                        text += text_run.get('content', '')
            
            elif 'table' in element:
                for row in element.get('table', {}).get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        text += self._extract_text(cell.get('content', []))
            
            elif 'tableOfContents' in element:
                text += self._extract_text(element.get('tableOfContents', {}).get('content', []))
                
        return text

    def extract_doc_id(url_or_id: str) -> str:
        if not url_or_id:
            raise ValueError("Provided URL or ID is empty.")
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_or_id)
        return match.group(1) if match else url_or_id

# # Usage Execution
# if __name__ == "__main__":
#     # Fixed the `cfg` bug by using an environment variable or standard input
#     test_url = os.environ.get("DOCS_URL", "INSERT_YOUR_DOC_URL_OR_ID_HERE")
    
#     if test_url == "INSERT_YOUR_DOC_URL_OR_ID_HERE":
#         logging.warning("Please set the DOCS_URL environment variable or modify the test_url variable.")
#     else:
#         try:
#             TARGET_DOC_ID = extract_doc_id(test_url)
#             docs_reader = GoogleDocsService()
#             extracted_text = docs_reader.read_document(TARGET_DOC_ID)
            
#             if extracted_text and extracted_text.strip():
#                 print("\n--- Document Content ---")
#                 print(extracted_text)
#             else:
#                 logging.info("Document was read successfully but appears to contain no text.")
                
#         except Exception as e:
#             logging.error(f"Execution failed: {e}")
