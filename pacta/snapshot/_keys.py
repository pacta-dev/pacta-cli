# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from typing import Any

from pacta.snapshot.jsonutil import dumps_deterministic


def _safe_attr(obj: Any, name: str) -> Any:
    return getattr(obj, name) if hasattr(obj, name) else None


def node_key(n: Any) -> str:
    """
    Produce a stable, comparable key for an IRNode.
    Preference order:
    1) n.id
    2) n.key
    3) dumps(n.to_dict())
    4) dumps(vars(n))
    5) repr(n)
    """
    v = _safe_attr(n, "id")
    if v is not None:
        return str(v)

    v = _safe_attr(n, "key")
    if v is not None:
        return str(v)

    if hasattr(n, "to_dict"):
        return dumps_deterministic(n.to_dict())

    if hasattr(n, "__dict__"):
        return dumps_deterministic(vars(n))

    return repr(n)


def edge_key(e: Any) -> str:
    """
    Stable key for an IREdge.
    Preference order:
    1) e.id
    2) (e.from_id, e.to_id, e.kind/type/label)
    3) dumps(e.to_dict())
    """
    v = _safe_attr(e, "id")
    if v is not None:
        return str(v)

    from_id = _safe_attr(e, "from_id") or _safe_attr(e, "source") or _safe_attr(e, "from")
    to_id = _safe_attr(e, "to_id") or _safe_attr(e, "target") or _safe_attr(e, "to")
    kind = _safe_attr(e, "kind") or _safe_attr(e, "type") or _safe_attr(e, "label")

    if from_id is not None and to_id is not None:
        return f"{from_id}->{to_id}:{kind or ''}"

    if hasattr(e, "to_dict"):
        return dumps_deterministic(e.to_dict())

    if hasattr(e, "__dict__"):
        return dumps_deterministic(vars(e))

    return repr(e)
