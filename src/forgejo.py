import requests
import sys

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
