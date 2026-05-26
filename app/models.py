from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    status: str
    created_at: str


class RuleOut(BaseModel):
    id: int
    name: str
    source_account_id: int
    source_account_name: str
    source_chat_id: str
    source_chat_title: str
    dest_account_id: Optional[int]
    dest_account_name: Optional[str]
    dest_chat_id: Optional[str]
    dest_chat_title: Optional[str]
    forward_mode: str
    delivery_mode: str
    webhook_mode: str
    webhook_url: Optional[str]
    is_active: int
    created_at: str


class LogOut(BaseModel):
    id: int
    rule_id: int
    rule_name: str
    source_msg_id: Optional[int]
    status: str
    error: Optional[str]
    latency_ms: Optional[int]
    created_at: str


class WebhookConfigOut(BaseModel):
    id: int
    name: str
    url: str
    is_active: int


class DialogOut(BaseModel):
    chat_id: str
    title: str
    type: str
    username: Optional[str] = None
