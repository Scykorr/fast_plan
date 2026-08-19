"""TZ §10 — GitHub link upsert, checks status, PR body attach."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from delivery.models import DeliverySettings, DeliveryTask, TaskGitHubLink

logger = logging.getLogger(__name__)


def sync_primary_github_fields(task: DeliveryTask, link: TaskGitHubLink | None = None):
    """Mirror primary (or given) link onto legacy task GitHub columns."""
    if link is None:
        link = (
            task.github_links.filter(is_primary=True).first()
            or task.github_links.order_by("-updated_at").first()
        )
    if link is None:
        return
    if not link.is_primary:
        task.github_links.filter(is_primary=True).exclude(pk=link.pk).update(
            is_primary=False
        )
        link.is_primary = True
        link.save(update_fields=["is_primary", "updated_at"])
    task.github_repo = link.repo or task.github_repo
    task.github_branch = link.branch or task.github_branch
    task.github_commit = link.commit or task.github_commit
    commits = list(task.github_commits or [])
    sha = (link.commit or "").strip()
    if sha and sha not in commits:
        commits.append(sha)
        task.github_commits = commits
    task.github_pr_url = link.pr_url or task.github_pr_url
    task.github_pr_number = link.pr_number if link.pr_number is not None else task.github_pr_number
    task.github_pr_state = link.pr_state or task.github_pr_state
    task.github_checks_url = link.checks_url or task.github_checks_url
    task.github_checks_status = link.checks_status or task.github_checks_status
    task.save(
        update_fields=[
            "github_repo",
            "github_branch",
            "github_commit",
            "github_commits",
            "github_pr_url",
            "github_pr_number",
            "github_pr_state",
            "github_checks_url",
            "github_checks_status",
            "updated_at",
        ]
    )


def upsert_github_link(
    task: DeliveryTask,
    *,
    repo: str = "",
    branch: str = "",
    commit: str = "",
    pr_number=None,
    pr_url: str = "",
    pr_state: str = "",
    checks_url: str = "",
    checks_status: str = "",
    make_primary: bool = True,
) -> TaskGitHubLink:
    repo = (repo or task.github_repo or "").strip()
    link = None
    if pr_number and repo:
        link = task.github_links.filter(repo=repo, pr_number=pr_number).first()
    if link is None and branch and repo:
        link = (
            task.github_links.filter(repo=repo, branch=branch, pr_number=pr_number).first()
            if pr_number
            else task.github_links.filter(
                repo=repo, branch=branch, pr_number__isnull=True
            ).first()
        )
        if link is None and pr_number:
            link = task.github_links.filter(repo=repo, branch=branch).first()
    created = link is None
    if created:
        link = TaskGitHubLink(task=task, repo=repo)
    if repo:
        link.repo = repo
    if branch:
        link.branch = branch
    if commit:
        link.commit = commit[:64]
    if pr_number is not None:
        link.pr_number = int(pr_number)
    if pr_url:
        link.pr_url = pr_url
    if pr_state:
        link.pr_state = pr_state
    if checks_url:
        link.checks_url = checks_url
    if checks_status:
        link.checks_status = checks_status
    has_primary = task.github_links.filter(is_primary=True)
    if link.pk:
        has_primary = has_primary.exclude(pk=link.pk)
    if make_primary or created and not has_primary.exists():
        task.github_links.filter(is_primary=True).update(is_primary=False)
        link.is_primary = True
    link.save()
    if link.is_primary:
        sync_primary_github_fields(task, link)
    return link


def find_tasks_for_github(
    full_name: str, number=None, head: str = ""
) -> list[DeliveryTask]:
    from django.db.models import Q

    q = Q(github_links__repo=full_name) | Q(github_repo=full_name)
    tasks: dict[int, DeliveryTask] = {}
    if number:
        for t in DeliveryTask.objects.filter(
            q & (Q(github_links__pr_number=number) | Q(github_pr_number=number))
        ).distinct().select_related("workspace"):
            tasks[t.id] = t
    if not tasks and head:
        for t in DeliveryTask.objects.filter(
            q
            & (
                Q(github_links__branch=head, github_links__pr_number__isnull=True)
                | Q(github_branch=head, github_pr_number__isnull=True)
            )
        ).distinct().select_related("workspace"):
            tasks[t.id] = t
    return list(tasks.values())


def pr_snippet_markdown(task: DeliveryTask, base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    return (
        f"\n\n## Fast Plan task\n"
        f"- Task: [{task.title}]({base}/agent-ops?task={task.id})\n"
        f"- Role: `{task.assignee_role or '—'}`\n"
        f"- DoD: {task.done_criterion or '—'}\n"
    )


def attach_task_link_to_pr(
    *,
    task: DeliveryTask,
    token: str,
    repo: str,
    pr_number: int,
    base_url: str,
    link: TaskGitHubLink | None = None,
) -> dict:
    """Append Fast Plan task markdown to GitHub PR body. Returns result dict."""
    api_url = f"https://api.github.com/repos/{repo}/pulls/{int(pr_number)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "fast-plan-agent-ops",
    }
    req = urllib.request.Request(api_url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        current = json.loads(resp.read().decode())
    body = current.get("body") or ""
    marker = f"/agent-ops?task={task.id}"
    if marker in body:
        if link and not link.attached_to_pr:
            link.attached_to_pr = True
            link.save(update_fields=["attached_to_pr", "updated_at"])
        return {
            "ok": True,
            "skipped": True,
            "detail": "Task link already present in PR body",
            "pr_url": current.get("html_url") or "",
        }
    snippet = pr_snippet_markdown(task, base_url)
    payload = json.dumps({"body": body + snippet}).encode()
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        updated = json.loads(resp.read().decode())
    if link:
        link.attached_to_pr = True
        link.pr_url = updated.get("html_url") or link.pr_url
        link.pr_state = updated.get("state") or link.pr_state
        link.save(
            update_fields=["attached_to_pr", "pr_url", "pr_state", "updated_at"]
        )
        if link.is_primary:
            sync_primary_github_fields(task, link)
    return {
        "ok": True,
        "skipped": False,
        "pr_url": updated.get("html_url") or "",
    }


def maybe_auto_attach_pr(task: DeliveryTask, link: TaskGitHubLink, base_url: str = ""):
    """Best-effort attach when workspace has a PAT (TZ §10 desirable)."""
    if link.attached_to_pr or not link.pr_number or not link.repo:
        return
    settings_row = DeliverySettings.objects.filter(workspace_id=task.workspace_id).first()
    token = (settings_row.github_api_token if settings_row else "") or ""
    token = token.strip()
    if not token:
        return
    try:
        attach_task_link_to_pr(
            task=task,
            token=token,
            repo=link.repo,
            pr_number=link.pr_number,
            base_url=base_url or "https://app.local",
            link=link,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "auto-attach PR failed task=%s pr=%s#%s",
            task.id,
            link.repo,
            link.pr_number,
        )


def apply_check_status_from_payload(
    task: DeliveryTask,
    *,
    repo: str,
    sha: str = "",
    branch: str = "",
    pr_number=None,
    conclusion: str = "",
    status: str = "",
    html_url: str = "",
) -> TaskGitHubLink | None:
    """Update checks fields from check_run / check_suite / status webhooks."""
    normalized = (conclusion or status or "").lower()
    if normalized in ("success", "neutral", "completed"):
        # prefer conclusion when present
        pass
    if conclusion:
        checks_status = conclusion.lower()
    elif status:
        checks_status = status.lower()
    else:
        checks_status = ""
    link = upsert_github_link(
        task,
        repo=repo,
        branch=branch,
        commit=sha,
        pr_number=pr_number,
        checks_url=html_url,
        checks_status=checks_status,
        make_primary=False,
    )
    # Prefer matching existing primary / pr / branch
    if pr_number or branch or sha:
        candidates = task.github_links.filter(repo=repo)
        if pr_number:
            hit = candidates.filter(pr_number=pr_number).first()
        elif branch:
            hit = candidates.filter(branch=branch).first()
        else:
            hit = candidates.filter(commit=sha[:64]).first() if sha else None
        if hit:
            hit.checks_status = checks_status or hit.checks_status
            if html_url:
                hit.checks_url = html_url
            if sha:
                hit.commit = sha[:64]
            hit.save()
            if hit.is_primary:
                sync_primary_github_fields(task, hit)
            return hit
    return link
