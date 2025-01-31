# app/main.py
import os
from composio import Action, Composio # type: ignore

class GitHubAgent:
    def __init__(self):
        self.client = Composio(
            api_key=os.getenv("COMPOSIO_API_KEY"),
            github_token=os.getenv("GITHUB_TOKEN")
        )

    def execute_action(self, action: Action, params: dict):
        """Execute a Composio action"""
        try:
            result = self.client.execute(
                action=action,
                params=params
            )
            print(f"Action {action.name} executed successfully")
            return result
        except Exception as e:
            print(f"Error executing action: {str(e)}")
            return None

    def star_repo(self, owner: str, repo: str):
        """Star a repository"""
        return self.execute_action(
            Action.GITHUB_STAR_REPO,
            {"owner": owner, "repo": repo}
        )

    def create_repo(self, name: str, private: bool = False):
        """Create a new repository"""
        return self.execute_action(
            Action.GITHUB_CREATE_REPO,
            {"name": name, "private": private}
        )

    def delete_repo(self, owner: str, repo: str):
        """Delete a repository"""
        return self.execute_action(
            Action.GITHUB_DELETE_REPO,
            {"owner": owner, "repo": repo}
        )

    def toggle_visibility(self, owner: str, repo: str):
        """Toggle repository visibility"""
        return self.execute_action(
            Action.GITHUB_UPDATE_REPO_VISIBILITY,
            {"owner": owner, "repo": repo}
        )

if __name__ == "__main__":
    agent = GitHubAgent()
    
    # Example usage
    # agent.create_repo("test-repo", private=True)
    agent.star_repo("vansh-potpose", "ai-agents")
    # agent.toggle_visibility("your-username", "test-repo")
    # agent.delete_repo("your-username", "test-repo")