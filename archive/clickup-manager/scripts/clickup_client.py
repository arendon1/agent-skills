import os
import sys
import json
import requests
import argparse
import time
from datetime import datetime
from pathlib import Path
from collections import deque
from tqdm import tqdm


# Load .env file manually (Workspace > Skill Root)
def load_env(path):
    if path.exists():
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


# 1. Skill Root .env (Defaults)
skill_env = Path(__file__).resolve().parent.parent / ".env"
load_env(skill_env)

# 2. Workspace/CWD .env (Overrides)
cwd_env = Path.cwd() / ".env"
if cwd_env.resolve() != skill_env.resolve():
    load_env(cwd_env)

# Verify API Token
API_TOKEN = os.getenv("CLICKUP_PAT")
if not API_TOKEN:
    print("Error: CLICKUP_PAT environment variable not set.")
    sys.exit(1)


class CacheHandler:
    """Tiered local caching for ClickUp API responses."""

    def __init__(self, filename=".clickup_cache.json"):
        self.filename = Path.cwd() / filename
        self.discovery_ttl = 86400  # 24 hours
        self.ops_ttl = 7200  # 2 hours
        self.cache = self._load()

    def _load(self):
        if self.filename.exists():
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        try:
            with open(self.filename, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def _get_category(self, endpoint):
        discovery_keywords = ["team", "space", "folder", "list"]
        for kw in discovery_keywords:
            if (
                kw in endpoint.lower()
                and "/task" not in endpoint.lower()
                and "/tag" not in endpoint.lower()
            ):
                return "discovery"
        return "ops"

    def get(self, key, endpoint):
        entry = self.cache.get(key)
        if not entry:
            return None

        category = self._get_category(endpoint)
        ttl = self.discovery_ttl if category == "discovery" else self.ops_ttl

        if time.time() - entry["timestamp"] > ttl:
            del self.cache[key]
            self._save()
            return None
        return entry["data"]

    def set(self, key, data):
        self.cache[key] = {"timestamp": time.time(), "data": data}
        self._save()

    def invalidate(self, pattern=None):
        if not pattern:
            self.cache = {}
        else:
            # Simple invalidation: remove entries containing the pattern
            self.cache = {k: v for k, v in self.cache.items() if pattern not in k}
        self._save()

    def clear(self):
        if self.filename.exists():
            self.filename.unlink()
        self.cache = {}


class RateLimiter:
    """Manages 100 RPM with a visual progress bar."""

    def __init__(self, limit=100, period=60):
        self.limit = limit
        self.period = period
        self.requests = deque()
        self.pbar = None

    def _init_pbar(self):
        if self.pbar is None:
            self.pbar = tqdm(
                total=self.limit,
                desc="ClickUp RPM",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} req/min",
                leave=True,
            )

    def wait_if_needed(self):
        self._init_pbar()
        now = time.time()
        # Remove requests older than the period
        while self.requests and now - self.requests[0] > self.period:
            self.requests.popleft()

        # If limit reached, wait
        if len(self.requests) >= self.limit:
            wait_time = self.period - (now - self.requests[0])
            if wait_time > 0:
                self.pbar.set_description("RPM Limit - Sleeping 😴")
                time.sleep(wait_time)
                self.pbar.set_description("ClickUp RPM")
                self.wait_if_needed()
                return

        self.requests.append(now)
        self.pbar.n = len(self.requests)
        self.pbar.refresh()


class MockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def __bool__(self):
        return self.status_code in [200, 201]


class ClickUpClient:
    def __init__(self, api_token, bypass_cache=False):
        self.headers = {"Authorization": api_token, "Content-Type": "application/json"}
        self.base_url_v2 = "https://api.clickup.com/api/v2"
        self.base_url_v3 = "https://api.clickup.com/api/v3"
        self.limiter = RateLimiter()
        self.cache = CacheHandler()
        self.bypass_cache = bypass_cache

    def _request(self, method, endpoint, version="v3", bypass_cache=None, **kwargs):
        """Unified request handler with v3-default and v2-fallback logic + Caching."""
        # Resolver preferencia de bypass_cache: parámetro -> instancia
        final_bypass = bypass_cache if bypass_cache is not None else self.bypass_cache

        base_url = self.base_url_v3 if version == "v3" else self.base_url_v2
        url = f"{base_url}/{endpoint.lstrip('/')}"

        # Cache Key: Method + URL + Query Params
        cache_params = kwargs.get("params", {})
        cache_key = f"{method}:{url}:{json.dumps(cache_params, sort_keys=True)}"

        if method == "GET" and not final_bypass:
            cached_data = self.cache.get(cache_key, endpoint)
            if cached_data:
                return MockResponse(cached_data)

        self.limiter.wait_if_needed()
        try:
            # Add timeout to requests
            response = requests.request(
                method, url, headers=self.headers, timeout=30, **kwargs
            )

            # Handle 401 Unauthorized
            if response.status_code == 401:
                print("Error: 401 Unauthorized. Check your CLICKUP_PAT.")
                return response

            # Targeted Invalidation on Write
            if method in ["POST", "PUT", "DELETE"]:
                resource = endpoint.split("/")[0]
                self.cache.invalidate(resource)

            if response.status_code in [200, 201] and method == "GET":
                self.cache.set(cache_key, response.json())

            if (
                version == "v3"
                and response.status_code in [404, 405]
                and method == "GET"
            ):
                return self._request(
                    method, endpoint, version="v2", bypass_cache=final_bypass, **kwargs
                )
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error en la petición: {e}")
            return None

    def format_output(self, data, format_type):
        """Format output based on request."""
        if format_type == "silent":
            return
        if format_type == "brief":
            if isinstance(data, list):
                summary = []
                for item in data:
                    # Handle name or comment_text
                    name = item.get("name") or item.get("comment_text", "Desconocido")
                    entry = f"ID: {item.get('id', '?')} | Contenido: {name}"
                    status = item.get("status")
                    if status:
                        status_val = (
                            status.get("status") if isinstance(status, dict) else status
                        )
                        entry += f" | Estado: {status_val}"
                    summary.append(entry)
                print("\n".join(summary))
            elif isinstance(data, dict):
                name = data.get("name") or data.get("comment_text", "Desconocido")
                entry = f"ID: {data.get('id', '?')} | Contenido: {name}"
                status = data.get("status")
                if status:
                    status_val = (
                        status.get("status") if isinstance(status, dict) else status
                    )
                    entry += f" | Estado: {status_val}"
                print(entry)
        else:
            print(json.dumps(data, indent=2))

    def parse_date(self, date_str, is_due=False):
        """Parse date from string to Epoch MS."""
        if not date_str:
            return None
        if date_str.isdigit():
            return int(date_str)
        formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if is_due:
                    dt = dt.replace(hour=23, minute=59, second=59)
                else:
                    dt = dt.replace(hour=0, minute=0, second=0)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        return None

    # --- Discovery & Hierarchy ---
    def list_workspaces(self, format_type="brief"):
        response = self._request("GET", "team", version="v2")
        if response and response.status_code == 200:
            data = response.json().get("teams", [])
            self.format_output(data, format_type)
            return data
        return []

    def list_spaces(self, team_id, format_type="brief"):
        response = self._request(
            "GET", f"team/{team_id}/space?archived=false", version="v2"
        )
        if response and response.status_code == 200:
            data = response.json().get("spaces", [])
            self.format_output(data, format_type)
            return data
        return []

    def list_folders(self, space_id, format_type="brief"):
        response = self._request(
            "GET", f"space/{space_id}/folder?archived=false", version="v2"
        )
        if response and response.status_code == 200:
            data = response.json().get("folders", [])
            self.format_output(data, format_type)
            return data
        return []

    def list_lists(self, folder_id=None, space_id=None, format_type="brief"):
        endpoint = f"folder/{folder_id}/list" if folder_id else f"space/{space_id}/list"
        response = self._request("GET", f"{endpoint}?archived=false", version="v2")
        if response and response.status_code == 200:
            data = response.json().get("lists", [])
            self.format_output(data, format_type)
            return data
        return []

    # --- Task Types & Discovery ---
    def list_custom_task_types(self, workspace_id, format_type="brief"):
        """Get custom task types for a workspace (v2 endpoint but consistent with v3 needs)."""
        cache_key = f"custom_items:{workspace_id}"
        cached = self.cache.get(cache_key, "team/custom_item")
        if cached:
            self.format_output(cached, format_type)
            return cached

        response = self._request(
            "GET", f"team/{workspace_id}/custom_item", version="v2"
        )
        if response and response.status_code == 200:
            data = response.json().get("custom_items", [])
            self.cache.set(cache_key, data)
            self.format_output(data, format_type)
            return data
        return []

    def resolve_task_type(self, workspace_id, type_name_or_id):
        """Heuristic to resolve a task type by name or ID using cache."""
        types = self.list_custom_task_types(workspace_id, format_type="silent")
        for t in types:
            # Check ID match
            if str(t.get("id")) == str(type_name_or_id):
                return t.get("id")
            # Check name match (case insensitive)
            if t.get("name", "").lower() == str(type_name_or_id).lower():
                return t.get("id")
        # Default fallback: return as is (might be a raw ID)
        return type_name_or_id

    # --- Task Management ---
    def list_tasks(
        self, list_id, status=None, assignee=None, search=None, format_type="brief"
    ):
        endpoint = f"list/{list_id}/task?archived=false"
        if status:
            endpoint += f"&statuses[]={status}"
        if assignee:
            endpoint += f"&assignees[]={assignee}"
        response = self._request("GET", endpoint, version="v2")
        if response and response.status_code == 200:
            tasks = response.json().get("tasks", [])
            if search:
                term = search.lower()
                tasks = [
                    t
                    for t in tasks
                    if term in t.get("name", "").lower()
                    or term in t.get("description", "").lower()
                ]
            self.format_output(tasks, format_type)
            return tasks
        return []

    def get_task(self, task_id, format_type="brief"):
        response = self._request("GET", f"task/{task_id}", version="v2")
        if response and response.status_code == 200:
            data = response.json()
            self.format_output(data, format_type)
            return data
        return None

    def find_task_by_name(self, list_id, name, parent=None, format_type="brief"):
        """Search for a task by name in a list (exact match)."""
        tasks = self.list_tasks(list_id, search=name, format_type="silent")
        for t in tasks:
            if t.get("name") == name:
                # If parent specified, verify it matches
                if parent and t.get("parent") != parent:
                    continue
                self.format_output(t, format_type)
                return t
        return None

    def create_task(
        self,
        list_id,
        name,
        description=None,
        start_date=None,
        due_date=None,
        parent=None,
        priority=None,
        assignees=None,
        tags=None,
        status=None,
        task_type=None,
        time_estimate=None,
        custom_fields=None,
        check_exists=False,
        format_type="brief",
    ):
        if check_exists:
            existing = self.find_task_by_name(
                list_id, name, parent=parent, format_type=format_type
            )
            if existing:
                print(f"Info: Tarea '{name}' ya existe. ID: {existing.get('id')}")
                return existing

        payload = {"name": name, "description": description or ""}
        if parent:
            payload["parent"] = parent
        if priority:
            payload["priority"] = int(priority)
        if status:
            payload["status"] = status
        if tags:
            payload["tags"] = tags if isinstance(tags, list) else [tags]
        if assignees:
            payload["assignees"] = (
                assignees if isinstance(assignees, list) else [assignees]
            )
        if time_estimate:
            payload["time_estimate"] = int(time_estimate)
        if custom_fields:
            payload["custom_fields"] = custom_fields

        if task_type:
            # We need workspace_id to resolve task type from cache/heuristics
            # Usually CLICKUP_TEAM_ID is available
            ws_id = os.getenv("CLICKUP_TEAM_ID")
            if ws_id:
                resolved_type = self.resolve_task_type(ws_id, task_type)
                payload["custom_item_id"] = resolved_type

        if start_date:
            v = self.parse_date(start_date)
            if v:
                payload["start_date"] = v
        if due_date:
            v = self.parse_date(due_date, is_due=True)
            if v:
                payload["due_date"] = v

        response = self._request(
            "POST", f"list/{list_id}/task", json=payload, version="v2"
        )
        if response and response.status_code == 200:
            data = response.json()
            self.format_output(data, format_type)
            return data
        return None

    def update_task(
        self,
        task_id,
        name=None,
        description=None,
        priority=None,
        status=None,
        start_date=None,
        due_date=None,
        parent=None,
        time_estimate=None,
        task_type=None,
        assignees_add=None,
        assignees_rem=None,
    ):
        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if priority:
            payload["priority"] = int(priority)
        if status:
            payload["status"] = status
        if parent:
            payload["parent"] = parent
        if time_estimate:
            payload["time_estimate"] = int(time_estimate)
        if task_type:
            ws_id = os.getenv("CLICKUP_TEAM_ID")
            if ws_id:
                payload["custom_item_id"] = self.resolve_task_type(ws_id, task_type)

        if start_date:
            payload["start_date"] = self.parse_date(start_date)
        if due_date:
            payload["due_date"] = self.parse_date(due_date, is_due=True)

        if assignees_add or assignees_rem:
            payload["assignees"] = {}
            if assignees_add:
                payload["assignees"]["add"] = (
                    assignees_add
                    if isinstance(assignees_add, list)
                    else [assignees_add]
                )
            if assignees_rem:
                payload["assignees"]["rem"] = (
                    assignees_rem
                    if isinstance(assignees_rem, list)
                    else [assignees_rem]
                )

        response = self._request("PUT", f"task/{task_id}", json=payload, version="v2")
        if response and response.status_code == 200:
            print(f"Task {task_id} updated.")
            return response.json()
        return None

    # --- Comments & Custom Fields ---
    def add_comment(self, task_id, text, notify_all=False):
        payload = {"comment_text": text, "notify_all": notify_all}
        return self._request(
            "POST", f"task/{task_id}/comment", json=payload, version="v2"
        )

    def list_comments(self, task_id, format_type="brief"):
        response = self._request("GET", f"task/{task_id}/comment", version="v2")
        if response and response.status_code == 200:
            data = response.json().get("comments", [])
            self.format_output(data, format_type)
            return data
        return []

    def set_custom_field(self, task_id, field_id, value):
        payload = {"value": value}
        return self._request(
            "POST", f"task/{task_id}/field/{field_id}", json=payload, version="v2"
        )

    def list_accessible_custom_fields(self, list_id, format_type="brief"):
        response = self._request("GET", f"list/{list_id}/field", version="v2")
        if response and response.status_code == 200:
            data = response.json().get("fields", [])
            self.format_output(data, format_type)
            return data
        return []

    # --- Free Tier Features ---
    def manage_tags(
        self, action, space_id=None, task_id=None, tag_name=None, format_type="brief"
    ):
        if action == "list":
            response = self._request("GET", f"space/{space_id}/tag", version="v2")
            if response and response.status_code == 200:
                data = response.json().get("tags", [])
                self.format_output(data, format_type)
                return data
        elif action == "add":
            # Check if tag already exists on the task to avoid redundancy
            task = self.get_task(task_id, format_type="silent")
            if task and tag_name in [t.get("name") for t in task.get("tags", [])]:
                print(f"Info: Tag '{tag_name}' ya está presente en la tarea {task_id}.")
                return None
            return self._request("POST", f"task/{task_id}/tag/{tag_name}", version="v2")
        elif action == "remove":
            return self._request(
                "DELETE", f"task/{task_id}/tag/{tag_name}", version="v2"
            )
        return None

    def upload_attachment(self, task_id, file_path):
        p = Path(file_path)
        if not p.exists():
            return None
        self.limiter.wait_if_needed()
        url = f"{self.base_url_v2}/task/{task_id}/attachment"
        with open(p, "rb") as f:
            files = {"attachment": (p.name, f)}
            response = requests.post(
                url,
                headers={"Authorization": self.headers["Authorization"]},
                files=files,
            )
            if response.status_code == 200:
                print(f"Uploaded {p.name} to task {task_id}")
                return response.json()
        return None

    def manage_dependencies(self, action, task_id, depends_on=None, dependency_id=None):
        if action == "add":
            return self._request(
                "POST",
                f"task/{task_id}/dependency",
                json={"depends_on": depends_on},
                version="v2",
            )
        elif action == "remove":
            return self._request(
                "DELETE",
                f"task/{task_id}/dependency?dependency_id={dependency_id}",
                version="v2",
            )
        return None

    def list_goals(self, team_id, format_type="brief"):
        response = self._request("GET", f"team/{team_id}/goal", version="v2")
        if response and response.status_code == 200:
            data = response.json().get("goals", [])
            self.format_output(data, format_type)
            return data
        return []

    # --- Docs & Pages (v3) ---
    def list_docs(self, team_id, format_type="brief"):
        response = self._request("GET", f"workspaces/{team_id}/docs", version="v3")
        if response and response.status_code == 200:
            data = response.json().get("docs", [])
            self.format_output(data, format_type)
            return data
        return []

    def create_doc(self, team_id, name, format_type="brief"):
        response = self._request(
            "POST", f"workspaces/{team_id}/docs", json={"name": name}, version="v3"
        )
        if response and response.status_code in [200, 201]:
            data = response.json().get("doc", response.json())
            self.format_output(data, format_type)
            return data
        return None

    def create_page(self, team_id, doc_id, name, content, content_format="text"):
        payload = {"name": name, "content": content, "content_format": content_format}
        return self._request(
            "POST",
            f"workspaces/{team_id}/docs/{doc_id}/pages",
            json=payload,
            version="v3",
        )

    # --- Bulk & Misc ---
    def bulk_create(self, list_id, tasks_data):
        results = []
        for t in tasks_data:
            res = self.create_task(
                list_id,
                t.get("name"),
                t.get("description"),
                t.get("start_date"),
                t.get("due_date"),
            )
            if res:
                results.append(res)
        return results


# Global Client Logic (Lazy)
_client_instance = None


def get_client(bypass_cache=None):
    global _client_instance
    if _client_instance is None:
        _client_instance = ClickUpClient(
            API_TOKEN, bypass_cache if bypass_cache is not None else False
        )
    elif bypass_cache is not None:
        _client_instance.bypass_cache = bypass_cache
    return _client_instance


# Bridge Functions for CLI
def list_teams(args):
    get_client().list_workspaces(args.format)


def list_spaces(args):
    get_client().list_spaces(args.team_id, args.format)


def list_folders(args):
    get_client().list_folders(args.space_id, args.format)


def list_lists(args):
    get_client().list_lists(args.folder_id, args.space_id, args.format)


def list_tasks(args):
    get_client().list_tasks(
        args.list_id, args.status, args.assignee, args.search, args.format
    )


def find_task(args):
    get_client().find_task_by_name(args.list_id, args.name, args.parent, args.format)


def get_task(args):
    get_client().get_task(args.task_id, args.format)


def create_task(args):
    # Parse custom fields if provided as JSON string
    cf = None
    if getattr(args, "custom_fields", None):
        try:
            cf = json.loads(args.custom_fields)
        except Exception:
            print("Warning: Could not parse custom_fields JSON.")

    get_client().create_task(
        args.list_id,
        args.name,
        args.description,
        args.start_date,
        args.due_date,
        args.parent,
        args.priority,
        args.assignees,
        args.tags,
        args.status,
        args.task_type,
        args.time_estimate,
        cf,
        args.check_exists,
        args.format,
    )


def update_task(args):
    get_client().update_task(
        args.task_id,
        args.name,
        args.description,
        args.priority,
        args.status,
        args.start_date,
        args.due_date,
        args.parent,
        args.time_estimate,
        args.task_type,
        args.assignees_add,
        args.assignees_rem,
    )


def manage_tags(args):
    get_client().manage_tags(
        args.action, args.space_id, args.task_id, args.tag_name, args.format
    )


def upload_attachment(args):
    get_client().upload_attachment(args.task_id, args.file)


def manage_dependencies(args):
    get_client().manage_dependencies(
        args.action,
        args.task_id,
        getattr(args, "depends_on", None),
        getattr(args, "dependency_id", None),
    )


def list_goals(args):
    get_client().list_goals(args.team_id, args.format)


def list_docs(args):
    get_client().list_docs(args.team_id, args.format)


def create_doc(args):
    get_client().create_doc(args.team_id, args.name, args.format)


def create_page(args):
    get_client().create_page(
        args.team_id, args.doc_id, args.name, args.content, args.content_format
    )


def bulk_create(args):
    try:
        tasks = (
            json.load(open(args.file, "r"))
            if os.path.exists(args.file)
            else json.loads(args.file)
        )
        get_client().bulk_create(args.list_id, tasks)
    except Exception as e:
        print(f"Error: {e}")


def list_task_types(args):
    get_client().list_custom_task_types(args.team_id, args.format)


def add_comment(args):
    get_client().add_comment(
        args.task_id, args.text, getattr(args, "notify_all", False)
    )


def list_comments(args):
    get_client().list_comments(args.task_id, args.format)


def set_custom_field(args):
    get_client().set_custom_field(args.task_id, args.field_id, args.value)


def list_custom_fields(args):
    get_client().list_accessible_custom_fields(args.list_id, args.format)


def manage_comments(args):
    if args.action == "list":
        get_client().list_comments(args.task_id, args.format)
    elif args.action == "add":
        get_client().add_comment(
            args.task_id, args.text, getattr(args, "notify_all", False)
        )


def manage_custom_fields(args):
    if args.action == "list":
        get_client().list_accessible_custom_fields(args.list_id, args.format)
    elif args.action == "set":
        get_client().set_custom_field(args.task_id, args.field_id, args.value)


def update_env_file(path, key, value):
    lines = []
    if path.exists():
        with open(path, "r") as f:
            lines = f.readlines()
    new_lines, found = [], False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    with open(path, "w") as f:
        f.writelines(new_lines)
    print(f"Updated {key}")


def select_item(items, item_type, optional=False):
    if not items:
        print(f"No {item_type} found.")
        return None
    print(f"\nAvailable {item_type}s:")
    for i, item in enumerate(items):
        print(f"{i + 1}. {item.get('name')} (ID: {item.get('id')})")
    while True:
        prompt = f"Select {item_type} (1-{len(items)})"
        if optional:
            prompt += " or press Enter to skip"
        choice = input(prompt + ": ")
        if optional and not choice.strip():
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        print("Invalid choice.")


def configure_context(args):
    if args.clear_cache:
        get_client().cache.clear()
        print("Cache base de datos de ClickUp eliminada.")
        return
    target_env = Path.cwd() / ".env"
    if any([args.team_id, args.space_id, args.folder_id, args.list_id]):
        if args.team_id:
            update_env_file(target_env, "CLICKUP_TEAM_ID", args.team_id)
        if args.space_id:
            update_env_file(target_env, "CLICKUP_SPACE_ID", args.space_id)
        if args.folder_id:
            update_env_file(target_env, "CLICKUP_FOLDER_ID", args.folder_id)
        if args.list_id:
            update_env_file(target_env, "CLICKUP_LIST_ID", args.list_id)
        return
    print("Configuration Wizard 🧙")
    ws = get_client().list_workspaces()
    w = select_item(ws, "Workspace")
    if w:
        update_env_file(target_env, "CLICKUP_TEAM_ID", w["id"])
        ss = get_client().list_spaces(w["id"])
        s = select_item(ss, "Space")
        if s:
            update_env_file(target_env, "CLICKUP_SPACE_ID", s["id"])
            fs = get_client().list_folders(s["id"])
            f = select_item(fs, "Folder", optional=True)
            if f:
                update_env_file(target_env, "CLICKUP_FOLDER_ID", f["id"])
                ls = get_client().list_lists(folder_id=f["id"])
                l = select_item(ls, "List", optional=True)
                if l:
                    update_env_file(target_env, "CLICKUP_LIST_ID", l["id"])
            else:
                ls = get_client().list_lists(space_id=s["id"])
                l = select_item(ls, "List", optional=True)
                if l:
                    update_env_file(target_env, "CLICKUP_LIST_ID", l["id"])


def main():
    parser = argparse.ArgumentParser(description="ClickUp Manager - Hybrid v3/v2")
    parser.add_argument(
        "--format", choices=["json", "brief", "silent"], default="brief"
    )
    parser.add_argument(
        "--bypass-cache", action="store_true", help="Omitir caché local"
    )
    sub = parser.add_subparsers(dest="command")

    # Config
    c_p = sub.add_parser("configure")
    c_p.add_argument("--team-id")
    c_p.add_argument("--space-id")
    c_p.add_argument("--folder-id")
    c_p.add_argument("--list-id")
    c_p.add_argument("--clear-cache", action="store_true", help="Limpiar caché local")
    c_p.set_defaults(func=configure_context)

    # Discovery
    sub.add_parser("list-teams").set_defaults(func=list_teams)

    ls_p = sub.add_parser("list-spaces")
    ls_p.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    ls_p.set_defaults(func=list_spaces)

    lf_p = sub.add_parser("list-folders")
    lf_p.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"))
    lf_p.set_defaults(func=list_folders)

    ll_p = sub.add_parser("list-lists")
    ll_p.add_argument("--folder-id", default=os.getenv("CLICKUP_FOLDER_ID"))
    ll_p.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"))
    ll_p.set_defaults(func=list_lists)

    # Tasks
    ft_p = sub.add_parser("find-task")
    ft_p.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"))
    ft_p.add_argument("--name", required=True)
    ft_p.add_argument("--parent")
    ft_p.set_defaults(func=find_task)

    tl_p = sub.add_parser("list-tasks")
    tl_p.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"))
    tl_p.add_argument("--status")
    tl_p.add_argument("--assignee")
    tl_p.add_argument("--search")
    tl_p.set_defaults(func=list_tasks)

    tc_p = sub.add_parser("create-task")
    tc_p.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"))
    tc_p.add_argument("--name", required=True)
    tc_p.add_argument("--description")
    tc_p.add_argument("--start-date")
    tc_p.add_argument("--due-date")
    tc_p.add_argument("--parent")
    tc_p.add_argument("--priority")
    tc_p.add_argument("--status")
    tc_p.add_argument("--assignees", nargs="+")
    tc_p.add_argument("--tags", nargs="+")
    tc_p.add_argument("--task-type", help="Name or ID of custom task type")
    tc_p.add_argument("--time-estimate", type=int, help="Time estimate in ms")
    tc_p.add_argument("--custom-fields", help="JSON string of custom fields")
    tc_p.add_argument(
        "--check-exists", action="store_true", help="Evitar duplicados por nombre"
    )
    tc_p.set_defaults(func=create_task)

    gt_p = sub.add_parser("get-task")
    gt_p.add_argument("--task-id", required=True)
    gt_p.set_defaults(func=get_task)

    tu_p = sub.add_parser("update-task")
    tu_p.add_argument("--task-id", required=True)
    tu_p.add_argument("--name")
    tu_p.add_argument("--description")
    tu_p.add_argument("--priority")
    tu_p.add_argument("--status")
    tu_p.add_argument("--start-date")
    tu_p.add_argument("--due-date")
    tu_p.add_argument("--parent")
    tu_p.add_argument("--time-estimate", type=int)
    tu_p.add_argument("--task-type")
    tu_p.add_argument("--assignees-add", nargs="+")
    tu_p.add_argument("--assignees-rem", nargs="+")
    tu_p.set_defaults(func=update_task)

    # Extras (Free)
    tag_p = sub.add_parser("manage-tags")
    tag_sub = tag_p.add_subparsers(dest="action", required=True)

    tag_list = tag_sub.add_parser("list")
    tag_list.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"))

    tag_add = tag_sub.add_parser("add")
    tag_add.add_argument("--task-id", required=True)
    tag_add.add_argument("--tag-name", required=True)

    tag_rem = tag_sub.add_parser("remove")
    tag_rem.add_argument("--task-id", required=True)
    tag_rem.add_argument("--tag-name", required=True)

    tag_p.set_defaults(func=manage_tags)

    att_p = sub.add_parser("upload-attachment")
    att_p.add_argument("--task-id", required=True)
    att_p.add_argument("--file", required=True)
    att_p.set_defaults(func=upload_attachment)

    # New Features
    ltt_p = sub.add_parser("list-task-types")
    ltt_p.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    ltt_p.set_defaults(func=list_task_types)

    com_p = sub.add_parser("manage-comments")
    com_sub = com_p.add_subparsers(dest="action", required=True)
    com_sub.add_parser("list").add_argument("--task-id", required=True)
    com_add = com_sub.add_parser("add")
    com_add.add_argument("--task-id", required=True)
    com_add.add_argument("--text", required=True)
    com_add.add_argument("--notify-all", action="store_true")
    com_p.set_defaults(
        func=manage_comments
    )  # We need to create manage_comments or fix bridge

    # Custom Fields
    cf_p = sub.add_parser("manage-custom-fields")
    cf_sub = cf_p.add_subparsers(dest="action", required=True)
    cf_sub.add_parser("list").add_argument(
        "--list-id", default=os.getenv("CLICKUP_LIST_ID")
    )
    cf_set = cf_sub.add_parser("set")
    cf_set.add_argument("--task-id", required=True)
    cf_set.add_argument("--field-id", required=True)
    cf_set.add_argument("--value", required=True)
    cf_p.set_defaults(func=manage_custom_fields)

    dep_p = sub.add_parser("manage-dependencies")
    dep_sub = dep_p.add_subparsers(dest="action", required=True)

    dep_add = dep_sub.add_parser("add")
    dep_add.add_argument("--task-id", required=True)
    dep_add.add_argument("--depends-on", required=True)

    dep_rem = dep_sub.add_parser("remove")
    dep_rem.add_argument("--task-id", required=True)
    dep_rem.add_argument("--dependency-id", required=True)

    dep_p.set_defaults(func=manage_dependencies)

    lg_p = sub.add_parser("list-goals")
    lg_p.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    lg_p.set_defaults(func=list_goals)

    # Docs
    ld_p = sub.add_parser("list-docs")
    ld_p.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    ld_p.set_defaults(func=list_docs)

    doc_cp = sub.add_parser("create-doc")
    doc_cp.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    doc_cp.add_argument("--name", required=True)
    doc_cp.set_defaults(func=create_doc)

    pag_cp = sub.add_parser("create-page")
    pag_cp.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"))
    pag_cp.add_argument("--doc-id", required=True)
    pag_cp.add_argument("--name", required=True)
    pag_cp.add_argument("--content")
    pag_cp.add_argument("--content-format", default="text")
    pag_cp.set_defaults(func=create_page)

    bc_p = sub.add_parser("bulk-create")
    bc_p.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"))
    bc_p.add_argument("--file", required=True)
    bc_p.set_defaults(func=bulk_create)

    args = parser.parse_args()
    get_client(args.bypass_cache)  # Initialize with flag
    try:
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()
    finally:
        # Clean shutdown of pbar if initialized
        if _client_instance and _client_instance.limiter.pbar:
            _client_instance.limiter.pbar.close()


if __name__ == "__main__":
    main()
