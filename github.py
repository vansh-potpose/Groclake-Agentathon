import os
import time
import requests
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class GitHubAgent:
    def __init__(self, token=None, use_browser=False, chrome_profile="Default"):
        self.token = token
        self.use_browser = use_browser
        self.chrome_profile = chrome_profile
        self.driver = None  # Initialize driver as None

        if token:
            self.headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }

        if use_browser:
            self._init_browser()  # ✅ Call browser initialization

    def _get_chrome_user_data_dir(self):
        """Get Chrome user data directory based on OS"""
        system = platform.system()
        if system == "Windows":
            return os.path.join(
                os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data"
            )
        elif system == "Darwin":
            return os.path.expanduser("~/Library/Application Support/Google/Chrome")
        else:  # Linux
            return os.path.expanduser("~/.config/google-chrome")

    def _init_browser(self):
        """Initialize Chrome browser with specified profile"""
        options = webdriver.ChromeOptions()

        # Configure profile settings
        user_data_dir = self._get_chrome_user_data_dir()
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--profile-directory={self.chrome_profile}")

        # Additional options for better stability
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-dev-shm-usage")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            print("✅ Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Chrome WebDriver: {e}")
            self.driver = None

    def _search_and_star_browser(self, owner, repo):
        """Browser automation to search and star a repository"""

        if self.driver is None:
            print("❌ Error: WebDriver is not initialized")
            return

        print(f"🔍 Searching for {owner}/{repo} on GitHub...")
        self.driver.get(f"https://github.com/{owner}/{repo}")

        try:
            star_button = self.driver.find_element(
                "xpath", "//button[contains(@aria-label, 'Star')]"
            )

            if "Star" in star_button.text:
                star_button.click()
                print(f"✅ Starred {owner}/{repo} via browser")
            else:
                print("⚠️ Repository already starred")

        except Exception as e:
            print(f"❌ Error during GitHub automation: {e}")

    def close(self):
        """Close the WebDriver if it's open"""
        if self.driver:
            self.driver.quit()
            print("🚪 Closed the browser.")

    def create_repository(self, name, description="", scope="public", add_readme=False):

        if self.driver is None:
            print("❌ Error: WebDriver is not initialized")
            return

        try:
            self.driver.get("https://github.com/")
            create_repo_btn = self.driver.find_element(
                "xpath", "//button[@id='global-create-menu-anchor']"
            )
            create_repo_btn.click()

            create_repo_link = self.driver.find_element("xpath", "//a[@href='/new']")
            create_repo_link.click()

            time.sleep(3)
            repo_name = self.driver.find_element(
                "xpath",
                "//input[@type='text'][contains(@aria-describedby, 'RepoNameInput')]",
            )
            print(repo_name.text)
            repo_name.send_keys(name)

            repo_desc = self.driver.find_element(
                "xpath", "//input[@name='Description']"
            )
            repo_desc.send_keys(description)

            if scope == "private":
                repo_visibility = self.driver.find_element(
                    "xpath", "//input[@name='visibilityGroup'][@value='private']"
                )
                repo_visibility.click()

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)
            if add_readme:
                repo_add_readme = self.driver.find_element(
                    "xpath", "//input[@type='checkbox']"
                )
                repo_add_readme.click()

            submit_btn = self.driver.find_element(
                "xpath", "//button[@type='submit'][text()='Create repository']"
            )
            submit_btn.click()

        except Exception as e:
            print(f"❌ Error during GitHub automation: {e}")


# Usage example
if __name__ == "__main__":
    # Choose between profiles (e.g., "Profile 1", "Profile 2", "Default")
    selected_profile = "Profile 2"  # Change this to your desired profile

    agent = GitHubAgent(
        token=os.getenv("GITHUB_TOKEN"),  # API token (optional)
        use_browser=True,
        chrome_profile=selected_profile,
    )

    try:
        agent.create_repository(
            name="demo",
            description="this is the demmo repo",
            scope="private",
            add_readme=True,
        )

        # agent._search_and_star_browser("vansh-potpose", "ai-agents")

        time.sleep(5)  # Keep browser open for observation
    finally:
        agent.close()
