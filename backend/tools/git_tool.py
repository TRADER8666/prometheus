from typing import Any, Dict


def _repo(path: str):
    try:
        import git  # type: ignore
    except Exception as e:
        raise RuntimeError(f"GitPython not installed: {e}")
    return git.Repo(path)


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    path = payload.get("path", ".")

    try:
        if action == "clone":
            import git  # type: ignore
            url = payload["url"]
            to_path = payload.get("to_path", ".")
            git.Repo.clone_from(url, to_path)
            return {"ok": True, "path": to_path}

        repo = _repo(path)

        if action == "status":
            return {"ok": True, "status": repo.git.status()}
        if action == "diff":
            return {"ok": True, "diff": repo.git.diff()[:20000]}
        if action == "log":
            max_count = int(payload.get("max_count", 10))
            logs = []
            for c in repo.iter_commits(max_count=max_count):
                logs.append({"hexsha": c.hexsha, "summary": c.summary, "author": str(c.author), "date": c.committed_datetime.isoformat()})
            return {"ok": True, "log": logs}
        if action == "branch":
            name = payload.get("name")
            checkout = bool(payload.get("checkout", True))
            b = repo.create_head(name)
            if checkout:
                b.checkout()
            return {"ok": True, "branch": name}
        if action == "checkout":
            branch = payload["branch"]
            repo.git.checkout(branch)
            return {"ok": True, "branch": branch}
        if action == "merge":
            branch = payload["branch"]
            repo.git.merge(branch)
            return {"ok": True, "merged": branch}
        if action == "commit_push":
            message = payload.get("message", "chore: update")
            remote = payload.get("remote", "origin")
            branch = payload.get("branch")
            repo.git.add(A=True)
            if repo.is_dirty(untracked_files=True):
                repo.index.commit(message)
            if branch:
                repo.git.push(remote, branch)
            else:
                repo.git.push()
            return {"ok": True, "message": message}

        return {"ok": False, "error": "Unknown action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
