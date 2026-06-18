from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import ADMIN_TOKEN


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if not ADMIN_TOKEN:
        return
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Ongeldige admin-token")
