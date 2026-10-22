"""Deliberately vulnerable support agent used to evaluate railguards-audit. Do not deploy."""
import subprocess
import urllib.request

from llm_client import chat_with_tools

from mail import inbox, smtp_send
from rag import search_documents

SYSTEM_PROMPT = "You are a helpful support agent. Use tools to answer the customer."


def read_inbox(limit: int = 20) -> list[dict]:
    return inbox.latest(limit)


def fetch_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")


def send_email(to: str, subject: str, body: str) -> str:
    smtp_send(to=to, subject=subject, body=body)
    return "sent"


def run_diagnostic(command: str) -> str:
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
    return result.stdout + result.stderr


def word_count(text: str) -> int:
    return len(text.split())


TOOLS = {
    "read_inbox": read_inbox,
    "fetch_url": fetch_url,
    "send_email": send_email,
    "run_diagnostic": run_diagnostic,
    "search_documents": search_documents,
    "word_count": word_count,
}


def handle_ticket(ticket_text: str, tenant_id: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": ticket_text}]
    while True:
        reply = chat_with_tools(messages, tools=list(TOOLS))
        if not reply.tool_calls:
            return reply.content
        for call in reply.tool_calls:
            output = TOOLS[call.name](**call.arguments)
            messages.append({"role": "tool", "name": call.name, "content": str(output)})
