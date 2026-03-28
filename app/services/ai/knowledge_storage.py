"""
MongoDB-backed AI knowledge: train, learn, act.

Collections:
  - ai_knowledge_base: Intent phrases and optional responses. scope=global (all tenants) or scope=tenant.
  - ai_documents: Raw documents for RAG (FAQ text, policies). Optional.
  - ai_embeddings: Vector embeddings for semantic search. Optional, for future "learn" step.
  - chat_sessions: Conversation session (tenant, channel, user_id).
  - chat_messages: Messages in a session (for training and context).
  - ai_training_data: Labeled examples (text, intent) for training / improving models.

General (global): e.g. "book" -> book_appointment for ALL tenants.
Tenant-specific: e.g. "refund policy" phrases or response text per tenant.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING

from app.helpers.date_utils import utcnow

logger = logging.getLogger(__name__)

# Default intent order (first match wins). Stored in DB or use this.
DEFAULT_INTENT_ORDER = [
    "cancel_appointment", "reschedule_appointment", "book_appointment",
    "suggest_professional", "professional_details",
    "check_price", "show_offers",
    "refund_policy", "delivery_eta", "order_status", "product_recommendation", "faq",
]


def _db():
    from app.services.db import get_db
    return get_db()


def _col(name: str):
    return _db().get_collection(name)


# ---------- ai_knowledge_base ----------
# Schema: { scope: "global"|"tenant", tenant?: string, intent: string, phrases: [string], response?: string, order?: int, updated_at }

def _ensure_ai_indexes():
    try:
        kb = _col("ai_knowledge_base")
        kb.create_index([("scope", ASCENDING), ("tenant", ASCENDING), ("intent", ASCENDING)])
        kb.create_index([("scope", ASCENDING)])
        kb.create_index([("tenant", ASCENDING)])
    except Exception as e:
        logger.warning("ai_knowledge_base index creation: %s", e)
    try:
        td = _col("ai_training_data")
        td.create_index([("tenant", ASCENDING), ("intent", ASCENDING)])
        td.create_index([("scope", ASCENDING)])
    except Exception as e:
        logger.warning("ai_training_data index creation: %s", e)
    try:
        cs = _col("chat_sessions")
        cs.create_index([("tenant", ASCENDING), ("channel", ASCENDING), ("user_id", ASCENDING)])
    except Exception as e:
        logger.warning("chat_sessions index creation: %s", e)
    try:
        cm = _col("chat_messages")
        cm.create_index([("session_id", ASCENDING), ("created_at", ASCENDING)])
    except Exception as e:
        logger.warning("chat_messages index creation: %s", e)


def get_intent_keywords_for_tenant(tenant: Optional[str]) -> tuple[Dict[str, List[str]], List[str]]:
    """
    Load intent_keywords and intent_keywords_order from MongoDB (ai_knowledge_base).
    Merges global (scope=global) + tenant (scope=tenant, tenant=tenant). Global applies to all; tenant adds phrases.
    Returns (intent_keywords dict, intent_order list). If DB has no global entries, seeds from code defaults then returns.
    """
    _ensure_ai_indexes()
    kb = _col("ai_knowledge_base")
    # Lazy seed: if no global rows, seed from code defaults once
    if kb.count_documents({"scope": "global"}) == 0:
        try:
            seed_global_intent_keywords()
        except Exception as e:
            logger.warning("seed_global_intent_keywords failed: %s", e)
    merged: Dict[str, List[str]] = {}
    order_seen: List[str] = []

    # Global first
    for doc in kb.find({"scope": "global"}).sort("order", 1):
        intent = (doc.get("intent") or "").strip()
        if not intent:
            continue
        phrases = doc.get("phrases")
        if isinstance(phrases, list):
            merged[intent] = list(merged.get(intent, [])) + [str(p).strip() for p in phrases if str(p).strip()]
        if intent not in order_seen:
            order_seen.append(intent)

    # Tenant-specific (add/override phrases per intent)
    if tenant:
        for doc in kb.find({"scope": "tenant", "tenant": tenant}).sort("order", 1):
            intent = (doc.get("intent") or "").strip()
            if not intent:
                continue
            phrases = doc.get("phrases")
            if isinstance(phrases, list):
                merged[intent] = list(merged.get(intent, [])) + [str(p).strip() for p in phrases if str(p).strip()]
            if intent not in order_seen:
                order_seen.append(intent)

    order = order_seen if order_seen else DEFAULT_INTENT_ORDER
    return merged, order


def list_knowledge_base(scope: Optional[str] = None, tenant: Optional[str] = None) -> List[Dict[str, Any]]:
    """List ai_knowledge_base entries. scope=global|tenant. If scope is None and tenant set, returns global + tenant entries for that tenant."""
    _ensure_ai_indexes()
    kb = _col("ai_knowledge_base")
    out = []
    if scope is None and tenant:
        for doc in kb.find({"scope": "global"}).sort("order", 1).sort("intent", 1):
            d = dict(doc)
            d.pop("_id", None)
            out.append(d)
        for doc in kb.find({"scope": "tenant", "tenant": tenant}).sort("order", 1).sort("intent", 1):
            d = dict(doc)
            d.pop("_id", None)
            out.append(d)
        return out
    q = {}
    if scope:
        q["scope"] = scope
    if scope == "tenant" and tenant:
        q["tenant"] = tenant
    for doc in kb.find(q).sort("order", 1).sort("intent", 1):
        d = dict(doc)
        d.pop("_id", None)
        out.append(d)
    return out


def upsert_knowledge_base(scope: str, intent: str, phrases: List[str], tenant: Optional[str] = None,
                          response: Optional[str] = None, order: Optional[int] = None) -> Dict[str, Any]:
    """Insert or update one ai_knowledge_base entry. scope=global|tenant. For global, tenant should be None."""
    _ensure_ai_indexes()
    kb = _col("ai_knowledge_base")
    now = utcnow()
    doc = {
        "scope": scope,
        "intent": intent,
        "phrases": [str(p).strip() for p in (phrases or []) if str(p).strip()],
        "updated_at": now,
    }
    if scope == "tenant" and tenant:
        doc["tenant"] = tenant
    if response is not None:
        doc["response"] = str(response).strip()
    if order is not None:
        doc["order"] = int(order)
    existing = kb.find_one({"scope": scope, "intent": intent, **({"tenant": tenant} if scope == "tenant" else {})})
    if existing:
        kb.update_one(
            {"_id": existing["_id"]},
            {"$set": doc}
        )
        doc["id"] = str(existing.get("_id"))
    else:
        ins = kb.insert_one(doc)
        doc["id"] = str(ins.inserted_id)
    doc.pop("_id", None)
    return doc


def delete_knowledge_base(scope: str, intent: str, tenant: Optional[str] = None) -> bool:
    """Remove one ai_knowledge_base entry."""
    kb = _col("ai_knowledge_base")
    q = {"scope": scope, "intent": intent}
    if scope == "tenant" and tenant:
        q["tenant"] = tenant
    res = kb.delete_one(q)
    return res.deleted_count > 0


# ---------- ai_training_data ----------
# Schema: { scope: "global"|"tenant", tenant?: string, intent: string, text: string, source?: string, created_at }

def add_training_example(tenant: Optional[str], scope: str, intent: str, text: str, source: Optional[str] = None) -> \
        Dict[str, Any]:
    """Add a labeled example for training. scope=global|tenant."""
    _ensure_ai_indexes()
    col = _col("ai_training_data")
    doc = {
        "scope": scope,
        "intent": intent,
        "text": (text or "").strip(),
        "created_at": utcnow(),
    }
    if scope == "tenant" and tenant:
        doc["tenant"] = tenant
    if source:
        doc["source"] = str(source)[:64]
    col.insert_one(doc)
    doc["id"] = str(doc.get("_id", ""))
    doc.pop("_id", None)
    return doc


def list_training_data(tenant: Optional[str] = None, intent: Optional[str] = None, limit: int = 500) -> List[
    Dict[str, Any]]:
    """List ai_training_data for export or review."""
    _ensure_ai_indexes()
    col = _col("ai_training_data")
    q = {}
    if tenant:
        q["tenant"] = tenant
    if intent:
        q["intent"] = intent
    out = []
    for doc in col.find(q).sort("created_at", -1).limit(limit):
        d = dict(doc)
        d["id"] = str(d.pop("_id", ""))
        out.append(d)
    return out


# ---------- ai_documents (for RAG / future) ----------
# Schema: { tenant?: string, scope: "global"|"tenant", type: "faq"|"policy"|"product", title?: string, content: string, updated_at }

def add_document(tenant: Optional[str], scope: str, doc_type: str, content: str, title: Optional[str] = None) -> Dict[
    str, Any]:
    """Add a document for RAG. scope=global|tenant."""
    col = _col("ai_documents")
    doc = {
        "scope": scope,
        "type": doc_type,
        "content": (content or "").strip(),
        "updated_at": utcnow(),
    }
    if scope == "tenant" and tenant:
        doc["tenant"] = tenant
    if title:
        doc["title"] = str(title)[:256]
    col.insert_one(doc)
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


# ---------- chat_sessions / chat_messages (for context and training) ----------

def create_chat_session(tenant: str, channel: str, user_id: str) -> Dict[str, Any]:
    """Create or get existing chat session. user_id can be phone for WhatsApp."""
    _ensure_ai_indexes()
    col = _col("chat_sessions")
    existing = col.find_one({"tenant": tenant, "channel": channel, "user_id": user_id})
    if existing:
        d = dict(existing)
        d["id"] = str(d.pop("_id", ""))
        return d
    doc = {"tenant": tenant, "channel": channel, "user_id": user_id, "created_at": utcnow()}
    col.insert_one(doc)
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


def add_chat_message(session_id: str, role: str, content: str, intent: Optional[str] = None) -> Dict[str, Any]:
    """Append a message to a session. role=user|assistant."""
    _ensure_ai_indexes()
    col = _col("chat_messages")
    doc = {
        "session_id": session_id,
        "role": role,
        "content": (content or "").strip(),
        "created_at": utcnow(),
    }
    if intent:
        doc["intent"] = intent
    col.insert_one(doc)
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc


# ---------- ai_embeddings (placeholder for vector search later) ----------
# Schema: { doc_id, tenant?, embedding: [float], text?: string, intent?: string }

def get_embedding_collection():
    """Return ai_embeddings collection for future use."""
    return _col("ai_embeddings")


def seed_global_intent_keywords() -> int:
    """
    Seed ai_knowledge_base with global (general) intent phrases from code defaults.
    All tenants will use these unless they add tenant-specific entries.
    Idempotent: upserts so safe to call on startup or via admin API.
    """
    from app.services.ai.config_schema import DEFAULT_AI_CONFIG
    keywords = DEFAULT_AI_CONFIG.get("intent_keywords") or {}
    order_list = DEFAULT_AI_CONFIG.get("intent_keywords_order") or DEFAULT_INTENT_ORDER
    order_map = {intent: i for i, intent in enumerate(order_list)}
    _ensure_ai_indexes()
    kb = _col("ai_knowledge_base")
    count = 0
    for intent, phrases in keywords.items():
        if not intent or not isinstance(phrases, list):
            continue
        upsert_knowledge_base(scope="global", intent=intent, phrases=phrases, order=order_map.get(intent, 99))
        count += 1
    return count
