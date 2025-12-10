"""
Lightweight Jira to Vectara Ingestion Tool

Simple script to crawl Jira issues using JQL and index them into Vectara.
No document processing, no ML dependencies - just API calls.
"""

import logging
import sys
from typing import Dict, Any, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class VectaraIndexer:
    """Simple Vectara indexer for structured documents."""

    def __init__(
        self,
        api_key: str,
        corpus_key: str,
        customer_id: Optional[str] = None,
        ssl_verify: Union[bool, str] = True
    ):
        """
        Initialize Vectara indexer.

        Args:
            api_key: Vectara API key
            corpus_key: Corpus key (numeric ID or string key)
            customer_id: Customer ID (optional, extracted from API key if not provided)
            ssl_verify: SSL verification. Can be:
                - True: Verify using system CA certificates (default)
                - False: Disable SSL verification (not recommended)
                - str: Path to custom CA certificate file or directory
        """
        self.api_key = api_key
        self.corpus_key = corpus_key
        self.customer_id = customer_id or self._extract_customer_id(api_key)
        self.base_url = "https://api.vectara.io"
        self.ssl_verify = ssl_verify

    def _extract_customer_id(self, api_key: str) -> str:
        """Extract customer ID from JWT token."""
        try:
            import base64
            import json
            # JWT format: header.payload.signature
            payload = api_key.split('.')[1]
            # Add padding if needed
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += '=' * padding
            decoded = base64.b64decode(payload)
            data = json.loads(decoded)
            return str(data.get('customer_id', ''))
        except Exception as e:
            logger.warning(f"Could not extract customer_id from API key: {e}")
            return ""

    def index_document(self, document: Dict[str, Any]) -> bool:
        """
        Index a document to Vectara.

        Args:
            document: Document dict with id, title, metadata, and sections

        Returns:
            bool: True if successful, False otherwise
        """
        url = f"{self.base_url}/v2/corpora/{self.corpus_key}/documents"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key
        }

        # Build document payload
        payload = {
            "id": document["id"],
            "type": "structured",
            "metadata": document.get("metadata", {}),
            "sections": []
        }

        # Add title if present
        if "title" in document and document["title"]:
            payload["title"] = document["title"]

        # Add sections
        for section in document.get("sections", []):
            section_data = {"text": section["text"]}
            if "title" in section and section["title"]:
                section_data["title"] = section["title"]
            if "metadata" in section:
                section_data["metadata"] = section["metadata"]
            payload["sections"].append(section_data)

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30,
                verify=self.ssl_verify
            )

            if response.status_code == 200:
                logger.info(f"Successfully indexed document: {document['id']}")
                return True
            elif response.status_code == 409:
                logger.info(f"Document already exists: {document['id']}")
                return True
            else:
                logger.error(f"Failed to index document {document['id']}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error indexing document {document['id']}: {e}")
            return False


class JiraCrawler:
    """Simple Jira crawler using REST API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        jql: str,
        indexer: VectaraIndexer,
        api_version: int = 3,
        max_results: int = 100,
        ssl_verify: Union[bool, str] = True
    ):
        """
        Initialize Jira crawler.

        Args:
            base_url: Jira base URL (e.g., https://your-domain.atlassian.net)
            username: Jira username/email
            api_token: Jira API token
            jql: JQL query to filter issues
            indexer: VectaraIndexer instance
            api_version: Jira API version (2 or 3)
            max_results: Maximum results per page
            ssl_verify: SSL verification. Can be:
                - True: Verify using system CA certificates (default)
                - False: Disable SSL verification (not recommended)
                - str: Path to custom CA certificate file or directory
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.jql = jql
        self.indexer = indexer
        self.api_version = api_version
        self.max_results = max_results
        self.ssl_verify = ssl_verify

        # Setup session with retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def extract_adf_text(self, adf_content: Any) -> str:
        """
        Extract plain text from Atlassian Document Format (ADF).

        Args:
            adf_content: ADF content structure (dict, list, or str)

        Returns:
            str: Extracted plain text
        """
        if not adf_content:
            return ""

        if isinstance(adf_content, str):
            return adf_content

        if isinstance(adf_content, dict):
            content_type = adf_content.get("type", "")

            # Text node
            if content_type == "text":
                return adf_content.get("text", "")

            # Block elements with newlines
            if content_type in ["paragraph", "heading"]:
                text_parts = []
                for item in adf_content.get("content", []):
                    text_parts.append(self.extract_adf_text(item))
                return "".join(text_parts) + "\n\n"

            # Lists
            if content_type in ["bulletList", "orderedList"]:
                list_items = []
                for item in adf_content.get("content", []):
                    list_items.append("• " + self.extract_adf_text(item).strip())
                return "\n".join(list_items) + "\n\n"

            if content_type == "listItem":
                item_text = []
                for item in adf_content.get("content", []):
                    item_text.append(self.extract_adf_text(item))
                return "".join(item_text)

            # Code blocks
            if content_type == "codeBlock":
                code_text = []
                for item in adf_content.get("content", []):
                    code_text.append(self.extract_adf_text(item))
                return "[CODE: " + "".join(code_text) + "]\n\n"

            # Links
            if content_type == "inlineCard":
                url = adf_content.get("attrs", {}).get("url", "")
                return f"[{url}] "

            # Document root
            if content_type == "doc":
                doc_parts = []
                for item in adf_content.get("content", []):
                    doc_parts.append(self.extract_adf_text(item))
                return "".join(doc_parts)

            # Generic: recursively process "content" array
            if "content" in adf_content:
                result = []
                for item in adf_content.get("content", []):
                    result.append(self.extract_adf_text(item))
                return "".join(result)

            return ""

        if isinstance(adf_content, list):
            result = []
            for item in adf_content:
                result.append(self.extract_adf_text(item))
            return "".join(result)

        return ""

    def crawl(self) -> int:
        """
        Crawl Jira issues and index to Vectara.

        Returns:
            int: Number of issues successfully indexed
        """
        logger.info(f"Starting Jira crawl with JQL: {self.jql}")

        headers = {"Accept": "application/json"}
        auth = (self.username, self.api_token)

        # Fields to retrieve
        fields = [
            "summary", "project", "issuetype", "status", "priority",
            "reporter", "assignee", "created", "updated", "resolutiondate",
            "labels", "comment", "description"
        ]

        issue_count = 0
        next_page_token = None
        start_at = 0

        while True:
            # Build request based on API version
            if self.api_version == 2:
                url = f"{self.base_url}/rest/api/2/search"
                params = {
                    "jql": self.jql,
                    "fields": ",".join(fields),
                    "maxResults": self.max_results,
                    "startAt": start_at
                }
                logger.info(f"Fetching page (API v2): startAt={start_at}")
            else:  # API v3
                url = f"{self.base_url}/rest/api/3/search/jql"
                params = {
                    "jql": self.jql,
                    "fields": ",".join(fields),
                    "maxResults": self.max_results
                }
                if next_page_token:
                    params["nextPageToken"] = next_page_token
                    logger.info(f"Fetching page (API v3): token={next_page_token[:20]}...")
                else:
                    logger.info("Fetching first page (API v3)")

            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    auth=auth,
                    params=params,
                    verify=self.ssl_verify,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

            except Exception as e:
                logger.error(f"Error fetching Jira issues: {e}")
                break

            issues = data.get("issues", [])
            if not issues:
                logger.info("No more issues to process")
                break

            logger.info(f"Processing {len(issues)} issues...")

            # Process each issue
            for issue in issues:
                try:
                    if self._process_issue(issue):
                        issue_count += 1
                except Exception as e:
                    logger.error(f"Error processing issue {issue.get('key', 'unknown')}: {e}")
                    continue

            # Check pagination
            if self.api_version == 2:
                start_at += len(issues)
                total = data.get("total", 0)
                if start_at >= total:
                    logger.info("Reached end of results (API v2)")
                    break
            else:  # API v3
                is_last = data.get("isLast", True)
                if is_last:
                    logger.info("Reached last page (API v3)")
                    break
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    logger.info("No next page token, stopping")
                    break

        logger.info(f"Finished crawling. Indexed {issue_count} issues.")
        return issue_count

    def _process_issue(self, issue: Dict[str, Any]) -> bool:
        """
        Process a single Jira issue and index to Vectara.

        Args:
            issue: Jira issue data

        Returns:
            bool: True if successfully indexed
        """
        issue_key = issue.get("key", "unknown")
        fields = issue.get("fields", {})

        # Extract metadata
        metadata = {
            "source": "jira",
            "url": f"{self.base_url}/browse/{issue_key}",
        }

        # Add optional fields safely
        if fields.get("project"):
            metadata["project"] = fields["project"].get("name", "")
        if fields.get("issuetype"):
            metadata["issueType"] = fields["issuetype"].get("name", "")
        if fields.get("status"):
            metadata["status"] = fields["status"].get("name", "")
        if fields.get("priority"):
            metadata["priority"] = fields["priority"].get("name", "")
        if fields.get("reporter"):
            metadata["reporter"] = fields["reporter"].get("displayName", "")
        if fields.get("assignee"):
            metadata["assignee"] = fields["assignee"].get("displayName", "")
        if fields.get("created"):
            metadata["created"] = fields["created"]
        if fields.get("updated"):
            metadata["last_updated"] = fields["updated"]
        if fields.get("resolutiondate"):
            metadata["resolved"] = fields["resolutiondate"]
        if fields.get("labels"):
            metadata["labels"] = fields["labels"]

        # Extract description
        description_content = fields.get("description")
        if description_content:
            description = self.extract_adf_text(description_content)
        else:
            description = ""

        if not description.strip():
            description = f"Issue: {issue_key}"

        # Extract comments
        comments_data = fields.get("comment", {}).get("comments", [])
        comments = []
        for comment in comments_data:
            author = comment.get("author", {}).get("displayName", "Unknown")
            try:
                comment_body = self.extract_adf_text(comment.get("body", {}))
                if comment_body.strip():
                    comments.append(f"{author}: {comment_body.strip()}")
            except Exception as e:
                logger.debug(f"Failed to extract comment: {e}")
                continue

        # Build document
        title = fields.get("summary", issue_key)
        status_text = fields.get("status", {}).get("name", "Unknown")

        document = {
            "id": issue_key,
            "title": title,
            "metadata": metadata,
            "sections": [
                {
                    "title": "Description",
                    "text": description
                },
                {
                    "title": "Comments",
                    "text": "\n\n".join(comments) if comments else "No comments"
                },
                {
                    "title": "Status",
                    "text": f"Issue {title} is {status_text}"
                }
            ]
        }

        # Index to Vectara
        success = self.indexer.index_document(document)
        if success:
            logger.info(f"✓ Indexed: {issue_key}")

        return success


def main():
    """Main entry point."""
    import argparse

    try:
        import yaml
    except ImportError:
        logger.error("PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Ingest Jira issues to Vectara")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    args = parser.parse_args()

    # Load config
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        sys.exit(1)

    # Parse config sections
    vectara_config = config.get("vectara", {})
    jira_config = config.get("jira", {})
    ssl_verify = config.get("ssl", {}).get("verify", True)

    # Validate required fields
    if not vectara_config.get("api_key"):
        logger.error("Missing required field: vectara.api_key")
        sys.exit(1)
    if not vectara_config.get("corpus_key"):
        logger.error("Missing required field: vectara.corpus_key")
        sys.exit(1)
    if not jira_config.get("base_url"):
        logger.error("Missing required field: jira.base_url")
        sys.exit(1)
    if not jira_config.get("username"):
        logger.error("Missing required field: jira.username")
        sys.exit(1)
    if not jira_config.get("api_token"):
        logger.error("Missing required field: jira.api_token")
        sys.exit(1)
    if not jira_config.get("jql"):
        logger.error("Missing required field: jira.jql")
        sys.exit(1)

    # Initialize indexer
    indexer = VectaraIndexer(
        api_key=vectara_config["api_key"],
        corpus_key=vectara_config["corpus_key"],
        customer_id=vectara_config.get("customer_id"),
        ssl_verify=ssl_verify
    )

    # Initialize crawler
    crawler = JiraCrawler(
        base_url=jira_config["base_url"],
        username=jira_config["username"],
        api_token=jira_config["api_token"],
        jql=jira_config["jql"],
        indexer=indexer,
        api_version=jira_config.get("api_version", 3),
        max_results=jira_config.get("max_results", 100),
        ssl_verify=ssl_verify
    )

    # Run crawl
    try:
        count = crawler.crawl()
        logger.info(f"✓ Complete! Indexed {count} issues.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
