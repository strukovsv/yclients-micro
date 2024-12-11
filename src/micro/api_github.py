import logging
import os

from github import Github, Auth


logger = logging.getLogger(__name__)

os.environ.get("YCLIENTS_DEBUG", "0")


async def savefile(filename: str, data):
    # Public Web Github
    g = Github(auth=Auth.Token(os.environ.get("GITHUB_TOKEN", "")))
    repo = g.get_repo(os.environ.get("GITHUB_REPO", ""))
    try:
        contents = repo.get_contents(
            filename, ref=os.environ.get("GITHUB_BRANCH", "master")
        )
        repo.update_file(
            path=filename,
            message=f"update file {filename}",
            content=data,
            branch="master",
            sha=contents.sha,
        )
    except Exception:
        repo.create_file(
            path=filename,
            message=f"create file {filename}",
            content=data,
            branch="master",
        )
