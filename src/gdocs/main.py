import re
import logging
import os
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1. PROPER LIBRARY LOGGING
# We create a logger specific to this module and add a NullHandler.
# This prevents our library from printing logs unless the user explicitly configures logging in their app.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Suppress noisy Google API logs
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)

# ---------------------------------------------------------
# STRATEGY PATTERN: Authentication
# ---------------------------------------------------------
class AuthStrategy(ABC):
    """Abstract base class for authentication strategies."""
    @abstractmethod
    def get_credentials(self) -> Any:
        pass

class DefaultAuthStrategy(AuthStrategy):
    """
    Attempts to intelligently authenticate using Colab if available, 
    otherwise falls back to local Application Default Credentials.
    """
    def get_credentials(self) -> Any:
        try:
            from google.colab import auth
            auth.authenticate_user()
            creds, _ = google.auth.default()
            logger.info("Authenticated using Google Colab environment.")
            return creds
        except ImportError:
            creds, _ = google.auth.default()
            logger.info("Authenticated using local Application Default Credentials.")
            return creds


# ---------------------------------------------------------
# UTILITY FUNCTIONS (Moved outside the class)
# ---------------------------------------------------------
def extract_doc_id(url_or_id: str) -> str:
    """Extracts the Google Doc ID from a full URL, or returns the ID if already clean."""
    if not url_or_id:
        raise ValueError("Provided URL or ID is empty.")
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_or_id)
    return match.group(1) if match else url_or_id


# ---------------------------------------------------------
# FACADE PATTERN: Google Docs API Service
# ---------------------------------------------------------
class GoogleDocsService:
    """
    A unified service class to handle Google Docs API operations.
    Uses Dependency Injection for authentication.
    """
    # 2. DEPENDENCY INJECTION
    # We pass the auth strategy in, defaulting to our smart DefaultAuthStrategy.
    def __init__(self, auth_strategy: Optional[AuthStrategy] = None):
        self._auth_strategy = auth_strategy or DefaultAuthStrategy()
        self._client = None

    @property
    def client(self):
        """Lazy initialization of the Google Docs API client."""
        if self._client is None:
            creds = self._auth_strategy.get_credentials()
            try:
                self._client = build('docs', 'v1', credentials=creds)
            except HttpError as e:
                raise RuntimeError(f"Failed to build Google Docs service: {e}")
        return self._client

    def get_tab_names(self, document_id: str) -> List[str]:
        try:
            document = self.client.documents().get(documentId=document_id).execute()
            tabs = document.get('tabs', [])
            tab_names = []
            
            if tabs:
                def extract_titles(tab_list):
                    for tab in tab_list:
                        title = tab.get('tabProperties', {}).get('title', 'Untitled Tab')
                        tab_names.append(title)
                        extract_titles(tab.get('childTabs', []))
                extract_titles(tabs)
            else:
                title = document.get('title', 'Untitled Document')
                tab_names.append(title)
                
            return tab_names
        except HttpError as err:
            logger.error(f"Google API Error: {err.status_code} - {err.reason}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return []

    def get_tabs_info(self, document_id: str) -> Dict[str, str]:
        try:
            document = self.client.documents().get(documentId=document_id).execute()
            tabs = document.get('tabs', [])
            tab_dict = {}
            
            if tabs:
                def extract_info(tab_list):
                    for tab in tab_list:
                        props = tab.get('tabProperties', {})
                        tab_id = props.get('tabId')
                        title = props.get('title', 'Untitled Tab')
                        
                        if tab_id:
                            tab_dict[tab_id] = title
                        extract_info(tab.get('childTabs', []))
                extract_info(tabs)
            return tab_dict
        except HttpError as err:
            logger.error(f"Google API Error: {err.status_code} - {err.reason}")
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return {}

    def read_specific_tab(self, document_id: str, target_tab_id: str) -> Optional[str]:
        try:
            document = self.client.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute()
            
            tabs = document.get('tabs', [])
            if tabs:
                def find_tab_content(tab_list):
                    for tab in tab_list:
                        if tab.get('tabProperties', {}).get('tabId') == target_tab_id:
                            doc_tab = tab.get('documentTab', {})
                            content = doc_tab.get('body', {}).get('content', [])
                            return self._extract_text(content)
                        
                        found_in_child = find_tab_content(tab.get('childTabs', []))
                        if found_in_child is not None:
                            return found_in_child
                    return None
                return find_tab_content(tabs)
            return None
        except Exception as e:
            logger.error(f"Failed to read specific tab: {e}")
            return None

    def read_document(self, document_id: str) -> Optional[str]:
        try:
            document = self.client.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute()
            
            full_text = ""
            tabs = document.get('tabs', [])
            
            if tabs:
                all_tabs = []
                def collect_tabs(tab_list):
                    for tab in tab_list:
                        all_tabs.append(tab)
                        collect_tabs(tab.get('childTabs', []))
                collect_tabs(tabs)
                
                for tab in all_tabs:
                    tab_title = tab.get('tabProperties', {}).get('title', 'Untitled Tab')
                    full_text += f"\n--- Tab: {tab_title} ---\n"
                    doc_tab = tab.get('documentTab', {})
                    content = doc_tab.get('body', {}).get('content', [])
                    full_text += self._extract_text(content)
            else:
                full_text = self._extract_text(document.get('body', {}).get('content', []))
            return full_text
        except HttpError as err:
            logger.error(f"Google API Error: {err.status_code} - {err.reason}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None

    def _extract_text(self, elements: List[Any]) -> str:
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

    def append_text(self, document_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        try:
            if not text.startswith('\n'):
                text = '\n' + text

            location = {'segmentId': ''}
            if tab_id:
                location['tabId'] = tab_id

            requests = [{'insertText': {'endOfSegmentLocation': location, 'text': text}}]
            self.client.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
            logger.info("Text appended successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to append text: {e}")
            return False

    def insert_text_at_start(self, document_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        try:
            if not text.endswith('\n'):
                text = text + '\n'

            location = {'index': 1, 'segmentId': ''}
            if tab_id:
                location['tabId'] = tab_id

            requests = [{'insertText': {'location': location, 'text': text}}]
            self.client.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
            logger.info("Text inserted at start successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False

    def replace_text(self, document_id: str, search_string: str, replacement_string: str) -> bool:
        try:
            requests = [{
                'replaceAllText': {
                    'containsText': {'text': search_string, 'matchCase': True},
                    'replaceText': replacement_string
                }
            }]
            self.client.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
            logger.info(f"Replaced all instances of '{search_string}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to replace text: {e}")
            return False
