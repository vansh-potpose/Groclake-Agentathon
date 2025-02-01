import os
import requests

class GitHubAgent:
    def __init__(self, token):
        if not token:
            raise ValueError("A GitHub token must be provided.")
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def star_repository(self, owner, repo):
        """Star a repository using the GitHub API."""
        url = f"{self.base_url}/user/starred/{owner}/{repo}"
        response = requests.put(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Successfully starred the repository {owner}/{repo}.")
        elif response.status_code == 304:
            print(f"⚠️ Repository {owner}/{repo} is already starred.")
        else:
            print(f"❌ Failed to star repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}")

    def unstar_repository(self, owner, repo):
        """Unstar a repository using the GitHub API."""
        url = f"{self.base_url}/user/starred/{owner}/{repo}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Successfully unstarred the repository {owner}/{repo}.")
        else:
            print(f"❌ Failed to unstar repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}")

    def create_repository(self, name, description="", scope="public", add_readme=False):
        """Create a new repository using the GitHub API."""
        url = f"{self.base_url}/user/repos"
        is_private = True if scope == "private" else False
        payload = {
            "name": name,
            "description": description,
            "private": is_private,
            "auto_init": add_readme  # Initializes the repo with a README if True.
        }
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code == 201:
            print(f"✅ Repository '{name}' created successfully.")
        else:
            print(f"❌ Failed to create repository '{name}'. Status Code: {response.status_code}, Response: {response.text}")

    def list_repositories(self):
        """List repositories for the authenticated user."""
        url = f"{self.base_url}/user/repos"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            repos = response.json()
            if repos:
                print("Your repositories:")
                for repo in repos:
                    visibility = "Private" if repo['private'] else "Public"
                    print(f"- {repo['full_name']} ({visibility})")
            else:
                print("No repositories found.")
        else:
            print(f"❌ Failed to fetch repositories. Status Code: {response.status_code}, Response: {response.text}")

    def delete_repository(self, owner, repo):
        """Delete a repository using the GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"✅ Repository {owner}/{repo} deleted successfully.")
        else:
            print(f"❌ Failed to delete repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}")

    def get_repository_details(self, owner, repo):
        """Retrieve details of a repository using the GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            details = response.json()
            print(f"Repository: {details['full_name']}")
            print(f"Description: {details.get('description', 'No description provided.')}")
            print(f"Visibility: {'Private' if details['private'] else 'Public'}")
            print(f"Stars: {details.get('stargazers_count', 0)}")
            print(f"Forks: {details.get('forks_count', 0)}")
        else:
            print(f"❌ Failed to get details for {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}")

    def fork_repository(self, owner, repo):
        """Fork a repository using the GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/forks"
        response = requests.post(url, headers=self.headers)
        if response.status_code in (202, 201):
            print(f"✅ Repository {owner}/{repo} forked successfully.")
        else:
            print(f"❌ Failed to fork repository {owner}/{repo}. Status Code: {response.status_code}, Response: {response.text}")

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")
    
    agent = GitHubAgent(token=token)
    
    while True:
        print("\nChoose an option:")
        print("1. Create a repository")
        print("2. Star a repository")
        print("3. Unstar a repository")
        print("4. List your repositories")
        print("5. Delete a repository")
        print("6. Get repository details")
        print("7. Fork a repository")
        print("8. Exit")
        choice = input("Enter your choice (1-8): ").strip()
        
        match choice:
            case "1":
                name = input("Enter repository name: ").strip()
                description = input("Enter repository description: ").strip()
                scope = input("Enter repository scope (public/private): ").strip().lower()
                add_readme = input("Initialize repository with README? (yes/no): ").strip().lower() == "yes"
                agent.create_repository(name=name, description=description, scope=scope, add_readme=add_readme)
            case "2":
                owner = input("Enter repository owner: ").strip()
                repo = input("Enter repository name: ").strip()
                agent.star_repository(owner=owner, repo=repo)
            case "3":
                owner = input("Enter repository owner: ").strip()
                repo = input("Enter repository name: ").strip()
                agent.unstar_repository(owner=owner, repo=repo)
            case "4":
                agent.list_repositories()
            case "5":
                owner = input("Enter repository owner (your username): ").strip()
                repo = input("Enter repository name: ").strip()
                confirm = input(f"Are you sure you want to delete {owner}/{repo}? This action cannot be undone (yes/no): ").strip().lower()
                if confirm == "yes":
                    agent.delete_repository(owner=owner, repo=repo)
                else:
                    print("Deletion canceled.")
            case "6":
                owner = input("Enter repository owner: ").strip()
                repo = input("Enter repository name: ").strip()
                agent.get_repository_details(owner=owner, repo=repo)
            case "7":
                owner = input("Enter repository owner to fork from: ").strip()
                repo = input("Enter repository name to fork: ").strip()
                agent.fork_repository(owner=owner, repo=repo)
            case "8":
                print("Exiting...")
                break
            case _:
                print("Invalid choice. Please select a number between 1 and 8.")

if __name__ == "__main__":
    main()
