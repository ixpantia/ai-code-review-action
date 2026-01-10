import requests
import sys
from urllib.parse import quote

class ForgejoClient:
    def __init__(self, api_url, token, repository):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.repository = repository
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }

    def get_pr_diff(self, pr_number):
        """Fetches the raw diff of a pull request."""
        url = f"{self.api_url}/repos/{self.repository}/pulls/{pr_number}.diff"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PR diff: {e}")
            return None

    def get_pull_request(self, pr_number):
        """Fetches pull request details."""
        url = f"{self.api_url}/repos/{self.repository}/pulls/{pr_number}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PR details: {e}")
            return None

    def get_file_content(self, path, ref):
        """Fetches the raw content of a file at a specific reference."""
        url = f"{self.api_url}/repos/{self.repository}/raw/{path}"
        params = {"ref": ref}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching file content for {path} at {ref}: {e}")
            return None

    def get_pr_comments(self, pr_number):
        """Fetches all comments on a pull request."""
        url = f"{self.api_url}/repos/{self.repository}/issues/{pr_number}/comments"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PR comments: {e}")
            return []

    def remove_label(self, pr_number, label_name):
        """Removes a label from a pull request."""
        encoded_label = quote(label_name)
        url = f"{self.api_url}/repos/{self.repository}/issues/{pr_number}/labels/{encoded_label}"
        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 204:
                return True
            elif response.status_code == 403:
                print(f"Failed to remove label {label_name}. Status code: 403 (Forbidden). "
                      "Ensure your token has write access to the repository.")
                return False
            else:
                print(f"Failed to remove label {label_name}. Status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error removing label: {e}")
            return False

    def post_pr_comment(self, pr_number, body):
        """Posts a comment to a pull request (issue comment API)."""
        url = f"{self.api_url}/repos/{self.repository}/issues/{pr_number}/comments"
        payload = {"body": body}

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            if response.status_code == 201:
                return True
            else:
                print(f"Failed to post comment. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error posting comment: {e}")
            return False
