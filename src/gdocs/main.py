import re
import logging
from typing import Optional

# Suppress the harmless httplib2 timeout warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)

from google.colab import auth
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class ColabGoogleDocsService:
    """
    A service class tailored for Google Colab environments to handle 
    Google Docs authentication and recursive reading operations.
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
        auth.authenticate_user()
        creds, _ = google.auth.default()
        
        try:
            return build('docs', 'v1', credentials=creds)
        except HttpError as e:
            raise RuntimeError(f"Failed to build Google Docs service: {e}")

    def read_document(self, document_id: str) -> Optional[str]:
        try:
            document = self.client.documents().get(documentId=document_id).execute()
            # Pass the entire structural content list to the recursive parser
            return self._extract_text(document.get('body', {}).get('content', []))
        except HttpError as err:
            print(f"Google API Error: {err.status_code} - {err.reason}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def _extract_text(self, elements: list) -> str:
        """
        Recursively parses all structural elements of the document JSON tree 
        (paragraphs, tables, lists) to extract text content.
        """
        text = ""
        for element in elements:
            # 1. Handle standard paragraphs (and list items, which are formatted as paragraphs)
            if 'paragraph' in element:
                for p_elem in element.get('paragraph', {}).get('elements', []):
                    text_run = p_elem.get('textRun', {})
                    if text_run:
                        text += text_run.get('content', '')
            
            # 2. Handle tables by recursively parsing each cell's content
            elif 'table' in element:
                for row in element.get('table', {}).get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        text += self._extract_text(cell.get('content', []))
            
            # 3. Handle Table of Contents
            elif 'tableOfContents' in element:
                text += self._extract_text(element.get('tableOfContents', {}).get('content', []))
                
        return text

def extract_doc_id(url_or_id: str) -> str:
    if not url_or_id:
        raise ValueError("Provided URL or ID is empty.")
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_or_id)
    return match.group(1) if match else url_or_id

# Usage Execution
if __name__ == "__main__":
    TARGET_DOC_ID = extract_doc_id(cfg.docs_url)
    
    try:
        docs_reader = ColabGoogleDocsService()
        extracted_text = docs_reader.read_document(TARGET_DOC_ID)
        
        if extracted_text and extracted_text.strip():
            print("--- Document Content ---")
            print(extracted_text)
        else:
            print("Document was read successfully but appears to contain no text.")
            
    except Exception as e:
        print(f"Execution failed: {e}")
