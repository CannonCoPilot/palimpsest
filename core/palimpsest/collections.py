"""Collections — named groupings of related projects, stored at the workspace root.

A collection groups projects that relate for co-analysis (the Compare tab). Two relationships
seed them: a derived subtext is auto-grouped with its parent (``kind="derived"``), and the user
can group any projects manually (``kind="manual"``). Persisted as a single ``collections.json``
so reads and writes stay atomic.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

COLLECTIONS_FILE = "collections.json"


def _path(workspace: Path) -> Path:
    return workspace / COLLECTIONS_FILE


def load_collections(workspace: Path) -> list[dict[str, Any]]:
    p = _path(workspace)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    cols = data.get("collections", []) if isinstance(data, dict) else []
    return cols if isinstance(cols, list) else []


def save_collections(workspace: Path, collections: list[dict[str, Any]]) -> None:
    _path(workspace).write_text(
        json.dumps({"collections": collections}, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _slugify(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")
    return s[:48] or "collection"


def _unique_id(existing: set[str], base: str) -> str:
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def create_collection(
    workspace: Path,
    label: str,
    description: str = "",
    project_ids: list[str] | None = None,
    kind: str = "manual",
    collection_id: str | None = None,
) -> dict[str, Any]:
    cols = load_collections(workspace)
    existing = {c["id"] for c in cols}
    cid = collection_id or _unique_id(existing, _slugify(label))
    # De-dupe members, preserve order.
    members: list[str] = []
    for pid in project_ids or []:
        if pid not in members:
            members.append(pid)
    col = {
        "id": cid,
        "label": label or cid,
        "description": description,
        "project_ids": members,
        "kind": kind,
    }
    cols.append(col)
    save_collections(workspace, cols)
    return col


def get_collection(workspace: Path, collection_id: str) -> dict[str, Any] | None:
    for c in load_collections(workspace):
        if c["id"] == collection_id:
            return c
    return None


def update_collection(
    workspace: Path, collection_id: str, *, label: str | None = None, description: str | None = None
) -> dict[str, Any] | None:
    cols = load_collections(workspace)
    found = None
    for c in cols:
        if c["id"] == collection_id:
            if label is not None:
                c["label"] = label
            if description is not None:
                c["description"] = description
            found = c
            break
    if found is not None:
        save_collections(workspace, cols)
    return found


def delete_collection(workspace: Path, collection_id: str) -> bool:
    cols = load_collections(workspace)
    kept = [c for c in cols if c["id"] != collection_id]
    if len(kept) == len(cols):
        return False
    save_collections(workspace, kept)
    return True


def add_member(workspace: Path, collection_id: str, project_id: str) -> dict[str, Any] | None:
    cols = load_collections(workspace)
    for c in cols:
        if c["id"] == collection_id:
            if project_id not in c["project_ids"]:
                c["project_ids"].append(project_id)
                save_collections(workspace, cols)
            return c
    return None


def remove_member(workspace: Path, collection_id: str, project_id: str) -> dict[str, Any] | None:
    cols = load_collections(workspace)
    for c in cols:
        if c["id"] == collection_id:
            if project_id in c["project_ids"]:
                c["project_ids"].remove(project_id)
                save_collections(workspace, cols)
            return c
    return None


def collections_for_project(workspace: Path, project_id: str) -> list[str]:
    """IDs of collections that contain ``project_id``."""
    return [c["id"] for c in load_collections(workspace) if project_id in c.get("project_ids", [])]


VALID_ROLES = ("member", "root")


def member_role(collection: dict[str, Any], project_id: str) -> str:
    """A member's collection-local role (FR-25). Default ``member`` (co-equal); ``root`` marks the
    per-view coordinate-backbone lens. Role is a property of the *collection*, not the project, so the
    same project can be a co-equal member of one collection and the root lens of another."""
    return collection.get("roles", {}).get(project_id, "member")


def set_member_role(
    workspace: Path, collection_id: str, project_id: str, role: str
) -> dict[str, Any] | None:
    """Set a member's collection-local role. ``role`` ∈ :data:`VALID_ROLES`. The project must already
    belong to the collection (else :class:`ValueError`). Only non-default (``root``) roles are stored,
    keeping the record clean. Returns the updated collection, or ``None`` if the collection is unknown."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}, got {role!r}")
    cols = load_collections(workspace)
    for c in cols:
        if c["id"] == collection_id:
            if project_id not in c.get("project_ids", []):
                raise ValueError(f"project {project_id!r} is not a member of collection {collection_id!r}")
            roles = c.get("roles", {})
            if role == "member":
                roles.pop(project_id, None)
            else:
                roles[project_id] = role
            if roles:
                c["roles"] = roles
            else:
                c.pop("roles", None)
            save_collections(workspace, cols)
            return c
    return None


def link_derived(
    workspace: Path, parent_id: str, parent_title: str, child_id: str, collection_id: str | None
) -> str:
    """Add ``parent_id`` + ``child_id`` to a collection (the named one, or an auto 'derived'
    collection for this parent). Returns the collection id."""
    if collection_id:
        add_member(workspace, collection_id, parent_id)
        add_member(workspace, collection_id, child_id)
        return collection_id
    auto_id = f"{parent_id}--subtexts"
    if get_collection(workspace, auto_id) is None:
        create_collection(
            workspace,
            label=f"{parent_title} + subtexts",
            description="A parent text and the subtexts derived from it.",
            project_ids=[parent_id, child_id],
            kind="derived",
            collection_id=auto_id,
        )
    else:
        add_member(workspace, auto_id, child_id)
    return auto_id
