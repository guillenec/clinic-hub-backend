# app/schemas/zoom.py
from datetime import datetime
from pydantic import BaseModel, Field

# ---------- TOKENS ----------
class ZoomTokenOut(BaseModel):
    user_id: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime
    revoked: bool | None = None

    class Config:
        from_attributes = True


# ---------- MEETING ----------
class ZoomMeetingOut(BaseModel):
    meeting_id: str
    start_url: str
    join_url: str
    passcode: str | None = None


class ZoomMeetingCreateResponse(BaseModel):
    ok: bool
    meeting: ZoomMeetingOut


# ---------- LINK ----------
class ZoomLinkOut(BaseModel):
    kind: str = Field(..., examples=["start_url", "join_url"])
    url: str
    passcode: str | None = None


# ---------- CLEANUP ----------
class ZoomCleanupOut(BaseModel):
    deleted: int
    cutoff: datetime
