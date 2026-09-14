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
    def get_tab_names(self, document_id: str) -> list[str]:
        """
        Retrieves a flattened list of all tab titles present in the document.
        Handles nested child tabs recursively.
        """
        try:
            # We do not need includeTabsContent=True just to read the metadata/titles
            document = self.client.documents().get(documentId=document_id).execute()
            
            tabs = document.get('tabs', [])
            tab_names = []
            
            if tabs:
                # Recursively extract titles from main tabs and nested child tabs
                def extract_titles(tab_list):
                    for tab in tab_list:
                        title = tab.get('tabProperties', {}).get('title', 'Untitled Tab')
                        tab_names.append(title)
                        # Traverse into child tabs if they exist
                        extract_titles(tab.get('childTabs', []))
                
                extract_titles(tabs)
            else:
                # Fallback for older documents that do not utilize the tabs feature
                title = document.get('title', 'Untitled Document')
                tab_names.append(title)
                
            return tab_names
            
        except HttpError as err:
            logging.error(f"Google API Error: {err.status_code} - {err.reason}")
            return []
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return []
    def get_tabs_info(self, document_id: str) -> dict:
        """
        Retrieves a dictionary mapping tab IDs to their corresponding titles.
        Handles nested child tabs recursively.
        """
        try:
            document = self.client.documents().get(documentId=document_id).execute()
            
            tabs = document.get('tabs', [])
            tab_dict = {}
            
            if tabs:
                # Recursively extract IDs and titles from main tabs and nested child tabs
                def extract_info(tab_list):
                    for tab in tab_list:
                        props = tab.get('tabProperties', {})
                        tab_id = props.get('tabId')
                        title = props.get('title', 'Untitled Tab')
                        
                        # Add to dictionary if tab_id exists
                        if tab_id:
                            tab_dict[tab_id] = title
                            
                        # Traverse into child tabs if they exist
                        extract_info(tab.get('childTabs', []))
                
                extract_info(tabs)
                
            return tab_dict
            
        except HttpError as err:
            logging.error(f"Google API Error: {err.status_code} - {err.reason}")
            return {}
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return {}
    def read_specific_tab(self, document_id: str, target_tab_id: str) -> Optional[str]:
        """
        Reads the document and extracts text only from the tab matching target_tab_id.
        """
        try:
            document = self.client.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute()
            
            tabs = document.get('tabs', [])
            
            if tabs:
                # Search recursively for the specific tab
                def find_tab_content(tab_list):
                    for tab in tab_list:
                        if tab.get('tabProperties', {}).get('tabId') == target_tab_id:
                            # Found it! Extract and return its text
                            doc_tab = tab.get('documentTab', {})
                            content = doc_tab.get('body', {}).get('content', [])
                            return self._extract_text(content)
                        
                        # Check child tabs
                        found_in_child = find_tab_content(tab.get('childTabs', []))
                        if found_in_child is not None:
                            return found_in_child
                            
                    return None # Not found in this branch
                
                return find_tab_content(tabs)
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to read specific tab: {e}")
            return None

    def read_document(self, document_id: str) -> Optional[str]:
        try:
            # 1. Fetch the document and explicitly request all tabs content
            document = self.client.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute()
            
            full_text = ""
            tabs = document.get('tabs', [])
            
            if tabs:
                # 2. Recursively collect all main tabs and nested child tabs
                all_tabs = []
                def collect_tabs(tab_list):
                    for tab in tab_list:
                        all_tabs.append(tab)
                        # Fetch nested tabs if they exist
                        collect_tabs(tab.get('childTabs', []))
                
                collect_tabs(tabs)
                
                # 3. Extract text from each tab
                for tab in all_tabs:
                    tab_title = tab.get('tabProperties', {}).get('title', 'Untitled Tab')
                    full_text += f"\n--- Tab: {tab_title} ---\n"
                    
                    # In the new structure, the body is inside 'documentTab'
                    doc_tab = tab.get('documentTab', {})
                    content = doc_tab.get('body', {}).get('content', [])
                    full_text += self._extract_text(content)
                    
            else:
                # Fallback just in case the document has no tabs or is an older format
                full_text = self._extract_text(document.get('body', {}).get('content', []))
                
            return full_text
            
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
    def append_text(self, document_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        """
        Appends text to the very end of the document (or specific tab).
        Ideal for continuously logging or adding AI-generated content.
        """
        try:
            # Ensure the inserted text starts on a new line
            if not text.startswith('\n'):
                text = '\n' + text

            location = {'segmentId': ''}
            if tab_id:
                location['tabId'] = tab_id

            requests = [{
                'insertText': {
                    'endOfSegmentLocation': location,
                    'text': text
                }
            }]
            
            self.client.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            logging.info("Text appended successfully.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to append text: {e}")
            return False

    def insert_text_at_start(self, document_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        """
        Inserts text at the very beginning of the document (Index 1).
        Great for adding executive summaries or intros at the top of a page.
        """
        try:
            # Ensure there is a line break after the insertion
            if not text.endswith('\n'):
                text = text + '\n'

            location = {'index': 1, 'segmentId': ''}
            if tab_id:
                location['tabId'] = tab_id

            requests = [{
                'insertText': {
                    'location': location,
                    'text': text
                }
            }]
            
            self.client.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            logging.info("Text inserted at start successfully.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to insert text: {e}")
            return False

    def replace_text(self, document_id: str, search_string: str, replacement_string: str) -> bool:
        """
        Replaces all exact matches of a string with new text. 
        Best for AI templates (e.g., replacing '{{AI_CONTENT}}' with actual generation).
        """
        try:
            requests = [{
                'replaceAllText': {
                    'containsText': {
                        'text': search_string,
                        'matchCase': True
                    },
                    'replaceText': replacement_string
                }
            }]
            
            self.client.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            logging.info(f"Replaced all instances of '{search_string}'.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to replace text: {e}")
            return False

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
