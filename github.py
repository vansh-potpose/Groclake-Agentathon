import os
import requests
import json
from flask import Flask, request, jsonify
from groclake.modellake import ModelLake
from groclake.vectorlake import VectorLake
from groclake.datalake import DataLake
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# Set your Groclake credentials and GitHub token.
# (These can also be set in your .env file.)
os.environ["GROCLAKE_API_KEY"] = os.getenv(
    "GROCLAKE_API_KEY", ""
)
os.environ["GROCLAKE_ACCOUNT_ID"] = os.getenv(
    "GROCLAKE_ACCOUNT_ID", ""
)

# Initialize the Groclake components. In a RAG task the vector & data lakes can be used
# to store and retrieve context if needed. Here we initialize them for completeness.
vectorlake = VectorLake()
datalake = DataLake()
modellake = ModelLake()


def call_modellake_chat(prompt):
    """
    Uses ModelLake to perform a chat completion.
    The chat is augmented with any available retrieval context via Groclake’s
    underlying vector and data lake (if configured).
    """
    chat_completion_request = {
        "groc_account_id": os.environ.get("GROCLAKE_ACCOUNT_ID"),
        "messages": [
            {
                "role": "system",
                "content": "You are a GitHub command parser. Output JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    response = modellake.chat_complete(chat_completion_request)
    answer = response.get("answer", "").strip()
    return answer


class GitHubAgent:
    def __init__(
        self,
        app,
        agent_name,
        initial_intent="github",
        intent_description="Handles GitHub operations",
        adaptor_config=None,
    ):
        if adaptor_config is None:
            adaptor_config = {}
        self.app = app
        self.agent_name = agent_name
        self.initial_intent = initial_intent
        self.intent_description = intent_description
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is not set.")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def default_handler(self, payload):
        try:
            query_text = payload.get("query_text", "No query provided")
            prompt = (
                "Context: Available GitHub operations:\n"
                "- create_repository: Create a repository. Requires 'name' (string), optional 'description' (string), 'scope' (public/private), 'add_readme' (boolean).\n"
                "- star_repository: Star a repository. Requires 'owner' (string), 'repo' (string).\n"
                "- unstar_repository: Unstar a repository. (Same parameters as starring.)\n"
                "- list_repositories: List the user’s repositories. No parameters.\n"
                "- delete_repository: Delete a repository. Requires 'owner' and 'repo'.\n"
                "- get_repository_details: Get repository details. Requires 'owner' and 'repo'.\n"
                "- fork_repository: Fork a repository. Requires 'owner' and 'repo'.\n"
                f"Command: {query_text}\n"
                "Output a JSON object with 'operation' (exactly one of the above) and any required parameters.\n"
                'Example 1: \'Create private repo test with README\' -> {"operation": "create_repository", "name": "test", "scope": "private", "add_readme": true}\n'
                'Example 2: \'Star octocat/hello\' -> {"operation": "star_repository", "owner": "octocat", "repo": "hello"}\n'
                "Output only the JSON, no markdown or additional text."
            )
            print(f"\nDEBUG: Prompt sent to ModelLake:\n{prompt}\n")
            answer = call_modellake_chat(prompt)
            print(f"DEBUG: ModelLake response: {answer}\n")

            # Remove any surrounding markdown code fences if present
            if answer.startswith("```json"):
                answer = answer[7:]
            if answer.endswith("```"):
                answer = answer[:-3]

            instructions = json.loads(answer)
            print(f"DEBUG: Parsed instructions: {instructions}\n")
        except json.JSONDecodeError as e:
            return {
                "response_text": f"Failed to parse instructions: {str(e)}",
                "status": 400,
                "query_text": query_text,
            }
        except Exception as e:
            return {
                "response_text": f"Error processing command: {str(e)}",
                "status": 500,
                "query_text": query_text,
            }

        operation = instructions.get("operation")
        if not operation:
            return {
                "response_text": "No operation specified in the instructions.",
                "status": 400,
                "query_text": query_text,
            }

        operation = operation.strip().lower()
        response_text = "Unknown operation."
        status = 400

        try:
            if operation == "create_repository":
                name = instructions.get("name")
                if not name:
                    raise ValueError("Missing 'name' for repository creation.")
                description = instructions.get("description", "")
                scope = instructions.get("scope", "public").strip().lower()
                add_readme = instructions.get("add_readme", False)
                # Ensure add_readme is a boolean
                if isinstance(add_readme, str):
                    add_readme = add_readme.lower() == "true"
                self.create_repository(name, description, scope, add_readme)
                response_text = f"Repository '{name}' created successfully."
                status = 200
            elif operation == "star_repository":
                owner = instructions.get("owner")
                repo = instructions.get("repo")
                if not owner or not repo:
                    raise ValueError("Missing 'owner' or 'repo' for starring.")
                self.star_repository(owner, repo)
                response_text = f"Starred {owner}/{repo}."
                status = 200
            elif operation == "unstar_repository":
                owner = instructions.get("owner")
                repo = instructions.get("repo")
                if not owner or not repo:
                    raise ValueError("Missing 'owner' or 'repo' for unstarring.")
                self.unstar_repository(owner, repo)
                response_text = f"Unstarred {owner}/{repo}."
                status = 200
            elif operation == "list_repositories":
                repos_output = self.list_repositories(return_output=True)
                response_text = repos_output
                status = 200
            elif operation == "delete_repository":
                owner = instructions.get("owner")
                repo = instructions.get("repo")
                if not owner or not repo:
                    raise ValueError("Missing 'owner' or 'repo' for deletion.")
                self.delete_repository(owner, repo)
                response_text = f"Repository {owner}/{repo} deleted successfully."
                status = 200
            elif operation == "get_repository_details":
                owner = instructions.get("owner")
                repo = instructions.get("repo")
                if not owner or not repo:
                    raise ValueError("Missing 'owner' or 'repo' for getting details.")
                details_output = self.get_repository_details(
                    return_output=True, owner=owner, repo=repo
                )
                response_text = details_output
                status = 200
            elif operation == "fork_repository":
                owner = instructions.get("owner")
                repo = instructions.get("repo")
                if not owner or not repo:
                    raise ValueError("Missing 'owner' or 'repo' for forking.")
                self.fork_repository(owner, repo)
                response_text = f"Repository {owner}/{repo} forked successfully."
                status = 200
            else:
                response_text = f"Operation '{operation}' is not supported."
                status = 400
        except Exception as e:
            response_text = f"Error executing operation: {str(e)}"
            status = 500

        return {
            "response_text": response_text,
            "status": status,
            "query_text": query_text,
        }

    # --- GitHub operation methods ---
    def create_repository(self, name, description="", scope="public", add_readme=False):
        is_private = True if scope == "private" else False
        payload = {
            "name": name,
            "description": description,
            "private": is_private,
            "auto_init": add_readme,
        }
        url = f"{self.base_url}/user/repos"
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code == 201:
            print(f"✅ Repository '{name}' created successfully.")
        else:
            print(
                f"❌ Failed to create repository '{name}'. Status Code: {response.status_code}, Response: {response.text}"
            )

    def star_repository(self, owner, repo):
        url = f"{self.base_url}/user/starred/{owner}/{repo}"
        response = requests.put(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Successfully starred repository {owner}/{repo}.")
        elif response.status_code == 304:
            print(f"⚠️ Repository {owner}/{repo} is already starred.")
        else:
            print(
                f"❌ Failed to star repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
            )

    def unstar_repository(self, owner, repo):
        url = f"{self.base_url}/user/starred/{owner}/{repo}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Successfully unstarred repository {owner}/{repo}.")
        else:
            print(
                f"❌ Failed to unstar repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
            )

    def list_repositories(self, return_output=False):
        url = f"{self.base_url}/user/repos"
        response = requests.get(url, headers=self.headers)
        output = ""
        if response.status_code == 200:
            repos = response.json()
            if repos:
                output += "Your repositories:\n"
                for repo in repos:
                    visibility = "Private" if repo["private"] else "Public"
                    output += f"- {repo['full_name']} ({visibility})\n"
            else:
                output = "No repositories found."
        else:
            output = f"❌ Failed to fetch repositories. Status Code: {response.status_code}, Response: {response.text}"
        return output if return_output else print(output)

    def delete_repository(self, owner, repo):
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Repository {owner}/{repo} deleted successfully.")
        else:
            print(
                f"❌ Failed to delete repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
            )

    def get_repository_details(self, return_output=False, owner=None, repo=None):
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        output = ""
        if response.status_code == 200:
            details = response.json()
            output += f"Repository: {details['full_name']}\n"
            output += f"Description: {details.get('description', 'No description provided.')}\n"
            output += f"Visibility: {'Private' if details['private'] else 'Public'}\n"
            output += f"Stars: {details.get('stargazers_count', 0)}\n"
            output += f"Forks: {details.get('forks_count', 0)}\n"
        else:
            output = f"❌ Failed to get details for {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
        return output if return_output else print(output)

    def fork_repository(self, owner, repo):
        url = f"{self.base_url}/repos/{owner}/{repo}/forks"
        response = requests.post(url, headers=self.headers)
        if response.status_code in (202, 201):
            print(f"✅ Repository {owner}/{repo} forked successfully.")
        else:
            print(
                f"❌ Failed to fork repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
            )


# Initialize the Flask app and GitHubAgent
app = Flask(__name__)
github_agent = GitHubAgent(app, "GitHubAgent")


@app.route("/agent", methods=["POST"])
def agent_endpoint():
    payload = request.get_json()
    result = github_agent.default_handler(payload)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
