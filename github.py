import os
import requests
import json
from flask import Flask, request, jsonify
from groq import Groq
from groclake.utillake import GrocAgent

def call_groq_chat(prompt):
    """
    Calls the Groq API to perform a chat completion using streaming mode.
    It accumulates the response chunks and returns the complete answer.
    """
    client = Groq()
    messages = [
        {"role": "system", "content": "You are a GitHub command parser. Output JSON."},
        {"role": "user", "content": prompt},
    ]
    # Create a chat completion request (using streaming to collect the answer)
    completion = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )
    answer = ""
    for chunk in completion:
        # Each chunk is assumed to have a choices list with a delta dict containing "content"
        delta = chunk.choices[0].delta
        answer += delta.content if delta.content is not None else ""
    return answer.strip()

class GitHubAgent(GrocAgent):
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
        super().__init__(
            app,
            agent_name,
            initial_intent,
            intent_description,
            self.default_handler,
            adaptor_config,
        )
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
                "- create_repository: Create repo. Requires 'name' (string), optional 'description' (string), 'scope' (public/private), 'add_readme' (boolean).\n"
                "- star_repository: Star a repo. Requires 'owner' (string), 'repo' (string).\n"
                "- unstar_repository: Unstar a repo. Same parameters as star.\n"
                "- list_repositories: List user's repos. No parameters.\n"
                "- delete_repository: Delete a repo. Requires 'owner' and 'repo'.\n"
                "- get_repository_details: Get repo info. Requires 'owner' and 'repo'.\n"
                "- fork_repository: Fork a repo. Requires 'owner' and 'repo'.\n"
                f"Command: {query_text}\n"
                "Output a JSON object with 'operation' (exactly one of the above) and parameters.\n"
                "Example 1: 'Create private repo test with README' -> {\"operation\": \"create_repository\", \"name\": \"test\", \"scope\": \"private\", \"add_readme\": true}\n"
                "Example 2: 'Star octocat/hello' -> {\"operation\": \"star_repository\", \"owner\": \"octocat\", \"repo\": \"hello\"}\n"
                "Output only the JSON, no markdown or additional text."
            )
            print(f"\nDEBUG: Prompt sent to Groq API:\n{prompt}\n")

            answer = call_groq_chat(prompt)
            print(f"DEBUG: Groq API response: {answer}\n")

            # Remove surrounding markdown code fences if present
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
                # Convert string booleans to actual booleans
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
                details_output = self.get_repository_details(return_output=True, owner=owner, repo=repo)
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
        if return_output:
            return output
        else:
            print(output)

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
        if return_output:
            return output
        else:
            print(output)

    def fork_repository(self, owner, repo):
        url = f"{self.base_url}/repos/{owner}/{repo}/forks"
        response = requests.post(url, headers=self.headers)
        if response.status_code in (202, 201):
            print(f"✅ Repository {owner}/{repo} forked successfully.")
        else:
            print(
                f"❌ Failed to fork repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}"
            )

app = Flask(__name__)
github_agent = GitHubAgent(app, "GitHubAgent")

@app.route("/agent", methods=["POST"])
def agent_endpoint():
    payload = request.get_json()
    result = github_agent.default_handler(payload)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
