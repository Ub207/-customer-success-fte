"""
MCP Server Prototype - Customer Success FTE Incubation Phase

This is the incubation-phase prototype using the MCP (Model Context Protocol)
server pattern. Tools are later migrated to production @function_tool decorators.
"""

import json
import uuid
import os
from enum import Enum
from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: mcp package not installed. Running in stub mode.")


# ---------------------------------------------------------------------------
# Channel Enum
# ---------------------------------------------------------------------------

class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# ---------------------------------------------------------------------------
# In-Memory Store
# ---------------------------------------------------------------------------

_tickets: dict[str, dict] = {}
_conversations: dict[str, list] = {}  # customer_id -> list of messages
_escalations: dict[str, dict] = {}    # ticket_id -> escalation info


def _load_knowledge_base() -> str:
    """Load the product docs from the context directory."""
    docs_path = Path(__file__).parent.parent / "context" / "product-docs.md"
    if docs_path.exists():
        return docs_path.read_text(encoding="utf-8")
    return ""


_KNOWLEDGE_BASE_TEXT = _load_knowledge_base()


# ---------------------------------------------------------------------------
# Core Tool Implementations
# ---------------------------------------------------------------------------

def _search_knowledge_base(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the product documentation for relevant information.

    Uses simple string matching against the product-docs.md file.
    In production this would use vector similarity search.
    """
    if not query or not _KNOWLEDGE_BASE_TEXT:
        return []

    query_lower = query.lower()
    results = []

    # Split into sections by ## headers
    sections = _KNOWLEDGE_BASE_TEXT.split("\n## ")
    for section in sections:
        if not section.strip():
            continue
        # Simple relevance: check if any query words appear in the section
        query_words = [w for w in query_lower.split() if len(w) > 3]
        section_lower = section.lower()
        match_count = sum(1 for word in query_words if word in section_lower)
        if match_count > 0:
            title_line = section.split("\n")[0].strip("# ").strip()
            snippet = " ".join(section.split()[:80])  # first ~80 words
            results.append({
                "title": title_line,
                "content": snippet,
                "relevance_score": match_count / max(len(query_words), 1),
            })

    # Sort by relevance and limit
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:max_results]


def _create_ticket(
    customer_id: str,
    issue: str,
    priority: str = "medium",
    channel: str = "email",
) -> dict:
    """
    Create a support ticket and store it in memory.

    Returns the ticket dict with id, status, and timestamps.
    """
    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.utcnow().isoformat()
    ticket = {
        "id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "priority": priority,
        "channel": channel,
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "escalated": False,
        "escalation_reason": None,
        "responses": [],
    }
    _tickets[ticket_id] = ticket

    # Initialize conversation history if not exists
    if customer_id not in _conversations:
        _conversations[customer_id] = []
    _conversations[customer_id].append({
        "ticket_id": ticket_id,
        "channel": channel,
        "issue": issue,
        "created_at": now,
    })

    return ticket


def _get_customer_history(customer_id: str) -> dict:
    """
    Retrieve full customer conversation history across all channels.

    Returns a dict with tickets and message history.
    """
    tickets_for_customer = [
        t for t in _tickets.values() if t["customer_id"] == customer_id
    ]
    history_entries = _conversations.get(customer_id, [])

    return {
        "customer_id": customer_id,
        "total_tickets": len(tickets_for_customer),
        "tickets": tickets_for_customer,
        "conversation_log": history_entries,
        "channels_used": list({t["channel"] for t in tickets_for_customer}),
    }


def _escalate_to_human(ticket_id: str, reason: str) -> dict:
    """
    Mark a ticket as escalated and route to appropriate human team.

    Reason codes and routing:
      - pricing_inquiry   -> billing@techcorp.io
      - refund_request    -> billing@techcorp.io
      - legal_threat      -> legal-support@techcorp.io
      - angry_customer    -> senior-support@techcorp.io
      - security_incident -> security@techcorp.io
      - knowledge_gap     -> support@techcorp.io
      - human_requested   -> support@techcorp.io
    """
    routing_map = {
        "pricing_inquiry": "billing@techcorp.io",
        "refund_request": "billing@techcorp.io",
        "legal_threat": "legal-support@techcorp.io",
        "angry_customer": "senior-support@techcorp.io",
        "security_incident": "security@techcorp.io",
        "knowledge_gap": "support@techcorp.io",
        "human_requested": "support@techcorp.io",
        "billing_inquiry": "billing@techcorp.io",
    }

    if ticket_id not in _tickets:
        return {"error": f"Ticket {ticket_id} not found"}

    ticket = _tickets[ticket_id]
    now = datetime.utcnow().isoformat()

    ticket["status"] = "escalated"
    ticket["escalated"] = True
    ticket["escalation_reason"] = reason
    ticket["escalated_at"] = now
    ticket["routed_to"] = routing_map.get(reason, "support@techcorp.io")

    escalation_record = {
        "ticket_id": ticket_id,
        "reason": reason,
        "routed_to": ticket["routed_to"],
        "escalated_at": now,
        "context_snapshot": ticket.copy(),
    }
    _escalations[ticket_id] = escalation_record

    sla_map = {
        "legal_threat": "1 hour",
        "security_incident": "1 hour",
        "angry_customer": "2 hours",
        "refund_request": "2 hours",
        "pricing_inquiry": "4 hours",
        "human_requested": "4 hours",
        "knowledge_gap": "4 hours",
    }

    return {
        "success": True,
        "ticket_id": ticket_id,
        "escalated_to": ticket["routed_to"],
        "reason": reason,
        "expected_sla": sla_map.get(reason, "4 hours"),
        "escalated_at": now,
    }


def _send_response(ticket_id: str, message: str, channel: str) -> dict:
    """
    Format and 'send' a response to the customer.

    In the prototype this stores the response. In production
    this calls the appropriate channel handler.
    """
    if ticket_id not in _tickets:
        return {"error": f"Ticket {ticket_id} not found"}

    ticket = _tickets[ticket_id]
    customer_id = ticket["customer_id"]
    now = datetime.utcnow().isoformat()

    # Format the message based on channel
    formatted = _format_for_channel(message, channel, ticket_id)

    response_record = {
        "response_id": str(uuid.uuid4()),
        "ticket_id": ticket_id,
        "channel": channel,
        "raw_message": message,
        "formatted_message": formatted,
        "sent_at": now,
        "delivery_status": "delivered",  # prototype: always delivered
    }

    ticket["responses"].append(response_record)
    ticket["updated_at"] = now
    ticket["status"] = "responded"

    # Log in conversation history
    if customer_id in _conversations:
        _conversations[customer_id].append({
            "type": "agent_response",
            "ticket_id": ticket_id,
            "channel": channel,
            "message": formatted,
            "sent_at": now,
        })

    return {
        "success": True,
        "ticket_id": ticket_id,
        "channel": channel,
        "formatted_message": formatted,
        "delivery_status": "delivered",
        "sent_at": now,
    }


def _format_for_channel(message: str, channel: str, ticket_id: str) -> str:
    """Format a response message according to channel-specific rules."""
    ch = channel.lower()

    if ch == Channel.EMAIL:
        return (
            f"Hi there,\n\n"
            f"{message}\n\n"
            f"Best regards,\n"
            f"TechCorp Support Team\n"
            f"---\n"
            f"Ticket: #{ticket_id}\n"
            f"This response was generated by our AI assistant."
        )

    elif ch == Channel.WHATSAPP:
        max_len = 300
        if len(message) > max_len:
            message = message[:max_len - 3] + "..."
        return f"{message}\n\nReply for more help or type 'human' for live support."

    else:  # web_form or default
        return (
            f"{message}\n\n"
            f"---\n"
            f"Need more help? Reply to this message or visit support.techcorp.io"
        )


# ---------------------------------------------------------------------------
# MCP Server Setup
# ---------------------------------------------------------------------------

if MCP_AVAILABLE:
    server = Server("customer-success-fte")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="search_knowledge_base",
                description="Search TechCorp product documentation for answers to customer questions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant documentation.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 5).",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="create_ticket",
                description="Create a support ticket for every customer interaction.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer email or phone number as unique ID.",
                        },
                        "issue": {
                            "type": "string",
                            "description": "Brief description of the customer's issue.",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Ticket priority level.",
                            "default": "medium",
                        },
                        "channel": {
                            "type": "string",
                            "enum": ["email", "whatsapp", "web_form"],
                            "description": "Channel the message arrived from.",
                        },
                    },
                    "required": ["customer_id", "issue", "channel"],
                },
            ),
            types.Tool(
                name="get_customer_history",
                description="Retrieve a customer's full conversation history across all channels.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer email or phone number.",
                        },
                    },
                    "required": ["customer_id"],
                },
            ),
            types.Tool(
                name="escalate_to_human",
                description="Escalate a ticket to a human agent for issues the AI cannot handle.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "The ticket ID to escalate.",
                        },
                        "reason": {
                            "type": "string",
                            "enum": [
                                "pricing_inquiry",
                                "refund_request",
                                "legal_threat",
                                "angry_customer",
                                "security_incident",
                                "knowledge_gap",
                                "human_requested",
                                "billing_inquiry",
                            ],
                            "description": "Reason code for the escalation.",
                        },
                    },
                    "required": ["ticket_id", "reason"],
                },
            ),
            types.Tool(
                name="send_response",
                description="Send a formatted response to the customer via their channel.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "The ticket ID this response belongs to.",
                        },
                        "message": {
                            "type": "string",
                            "description": "The response message content.",
                        },
                        "channel": {
                            "type": "string",
                            "enum": ["email", "whatsapp", "web_form"],
                            "description": "Channel to send the response on.",
                        },
                    },
                    "required": ["ticket_id", "message", "channel"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name == "search_knowledge_base":
            results = _search_knowledge_base(
                query=arguments["query"],
                max_results=arguments.get("max_results", 5),
            )
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "create_ticket":
            ticket = _create_ticket(
                customer_id=arguments["customer_id"],
                issue=arguments["issue"],
                priority=arguments.get("priority", "medium"),
                channel=arguments["channel"],
            )
            return [types.TextContent(type="text", text=json.dumps(ticket, indent=2))]

        elif name == "get_customer_history":
            history = _get_customer_history(customer_id=arguments["customer_id"])
            return [types.TextContent(type="text", text=json.dumps(history, indent=2))]

        elif name == "escalate_to_human":
            result = _escalate_to_human(
                ticket_id=arguments["ticket_id"],
                reason=arguments["reason"],
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "send_response":
            result = _send_response(
                ticket_id=arguments["ticket_id"],
                message=arguments["message"],
                channel=arguments["channel"],
            )
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    if not MCP_AVAILABLE:
        print("MCP package not available. Install with: pip install mcp")
        return

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="customer-success-fte",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
