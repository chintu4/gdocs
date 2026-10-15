import json
import re
import logging
import os
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)


class GoogleDocsError(RuntimeError):
    """Raised when a Google Docs API call fails.

    Previously these failures were swallowed and surfaced as an empty result
    (``{}``, ``None`` or ``False``), which made an access error impossible to
    distinguish from a document that simply had no content.
    """


def _api_error(action: str, doc_id: str, err: HttpError) -> "GoogleDocsError":
    """Build a readable GoogleDocsError from an HttpError, with a hint."""
    detail = ""
    try:
        payload = json.loads(err.content.decode("utf-8"))
        detail = payload.get("error", {}).get("message", "") or ""
    except Exception:
        detail = ""

    msg = f"{action} failed for document '{doc_id}': HTTP {err.status_code} ({err.reason})"
    if detail:
        msg += f" - {detail}"

    if err.status_code == 404:
        msg += (
            "\nThe document was not found, or the authenticated account cannot "
            "access it. If you are authenticating as a service account, share the "
            "document with the service account's email address (the client_email "
            "in its key JSON)."
        )
    elif err.status_code == 403:
        msg += (
            "\nAccess denied. Check that the Google Docs API (and Drive API) are "
            "enabled in the project and that the account has permission on the document."
        )
    return GoogleDocsError(msg)


class AuthStrategy(ABC):
    @abstractmethod
    def get_credentials(self) -> Any:
        pass

class DefaultAuthStrategy(AuthStrategy):
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

def _extract_doc_id(url_or_id: str) -> str:
    """INTERNAL: Extracts the Doc ID from a URL, or returns the ID if already clean."""
    if not url_or_id:
        raise ValueError("Provided URL or ID is empty.")
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_or_id)
    return match.group(1) if match else url_or_id

class GoogleDocsService:
    def __init__(self, auth_strategy: Optional[AuthStrategy] = None):
        self._auth_strategy = auth_strategy or DefaultAuthStrategy()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            creds = self._auth_strategy.get_credentials()
            try:
                self._client = build('docs', 'v1', credentials=creds)
            except HttpError as e:
                raise RuntimeError(f"Failed to build Google Docs service: {e}")
        return self._client

    def get_tab_names(self, url_or_id: str) -> List[str]:
        doc_id = _extract_doc_id(url_or_id)
        try:
            document = self.client.documents().get(
                documentId=doc_id,
                includeTabsContent=True
            ).execute()
        except HttpError as err:
            raise _api_error("get_tab_names", doc_id, err) from err

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

    def get_tabs_info(self, url_or_id: str) -> Dict[str, str]:
        doc_id = _extract_doc_id(url_or_id)
        try:
            document = self.client.documents().get(
                documentId=doc_id,
                includeTabsContent=True
            ).execute()
        except HttpError as err:
            raise _api_error("get_tabs_info", doc_id, err) from err

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

    def read_specific_tab(self, url_or_id: str, target_tab_id: str) -> Optional[str]:
        doc_id = _extract_doc_id(url_or_id)
        try:
            document = self.client.documents().get(
                documentId=doc_id,
                includeTabsContent=True
            ).execute()
        except HttpError as err:
            raise _api_error("read_specific_tab", doc_id, err) from err

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

    def read_document(self, url_or_id: str) -> Optional[str]:
        doc_id = _extract_doc_id(url_or_id)
        try:
            document = self.client.documents().get(
                documentId=doc_id,
                includeTabsContent=True
            ).execute()
        except HttpError as err:
            raise _api_error("read_document", doc_id, err) from err

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

    def append_text(self, url_or_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        doc_id = _extract_doc_id(url_or_id)
        if not text.startswith('\n'):
            text = '\n' + text

        location = {'segmentId': ''}
        if tab_id:
            location['tabId'] = tab_id

        requests = [{'insertText': {'endOfSegmentLocation': location, 'text': text}}]
        try:
            self.client.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        except HttpError as err:
            raise _api_error("append_text", doc_id, err) from err
        logger.info("Text appended successfully.")
        return True

    def append_to_tab_index(self, url_or_id: str, text: str, tab_index: int = 0) -> bool:
        """Convenience method to append text directly to a tab by its zero-based index."""
        tabs_info = self.get_tabs_info(url_or_id)
        tab_ids = list(tabs_info.keys())

        if not tab_ids:
            return self.append_text(url_or_id, text)

        if tab_index >= len(tab_ids):
            logger.error(f"Tab index {tab_index} out of bounds. Document has {len(tab_ids)} tab(s).")
            return False

        target_tab_id = tab_ids[tab_index]
        return self.append_text(url_or_id, text, tab_id=target_tab_id)

    def insert_text_at_start(self, url_or_id: str, text: str, tab_id: Optional[str] = None) -> bool:
        doc_id = _extract_doc_id(url_or_id)
        if not text.endswith('\n'):
            text = text + '\n'

        location = {'index': 1, 'segmentId': ''}
        if tab_id:
            location['tabId'] = tab_id

        requests = [{'insertText': {'location': location, 'text': text}}]
        try:
            self.client.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        except HttpError as err:
            raise _api_error("insert_text_at_start", doc_id, err) from err
        logger.info("Text inserted at start successfully.")
        return True

    def insert_to_tab_index(self, url_or_id: str, text: str, tab_index: int = 0) -> bool:
        """Convenience method to insert text at the start of a tab by its zero-based index."""
        tabs_info = self.get_tabs_info(url_or_id)
        tab_ids = list(tabs_info.keys())

        if not tab_ids:
            return self.insert_text_at_start(url_or_id, text)

        if tab_index >= len(tab_ids):
            logger.error(f"Tab index {tab_index} out of bounds. Document has {len(tab_ids)} tab(s).")
            return False

        target_tab_id = tab_ids[tab_index]
        return self.insert_text_at_start(url_or_id, text, tab_id=target_tab_id)

    def replace_text(self, url_or_id: str, search_string: str, replacement_string: str) -> bool:
        doc_id = _extract_doc_id(url_or_id)
        requests = [{
            'replaceAllText': {
                'containsText': {'text': search_string, 'matchCase': True},
                'replaceText': replacement_string
            }
        }]
        try:
            self.client.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        except HttpError as err:
            raise _api_error("replace_text", doc_id, err) from err
        logger.info(f"Replaced all instances of '{search_string}'.")
        return True
