"""The same experiment, run through the Claude Agent SDK instead of LangChain.

Why this file exists: a Claude.ai subscription and the Anthropic API Console
are separate billing systems, and a Pro or Max plan does not include API
access. The path that draws on the plan is the Agent SDK (or the Claude Code
CLI), which authenticates over OAuth rather than with an API key:

    npm install -g @anthropic-ai/claude-code
    claude setup-token

The three tools are exposed as an in process MCP server, and the guard sits
inside them exactly as it does in the LangChain version. Same policy, same
backend, same scenarios, same guarded and unguarded flip. The comparison is
always made within one framework, never across the two.

Two things to know before running it.

**ANTHROPIC_API_KEY shadows OAuth, silently.** Credentials resolve in order,
and an API key in the environment wins. You would be paying pay as you go while
believing you were on your plan. `_without_api_key` below removes it for the
duration of the call and puts it back afterwards.

**A plan is licensed for individual use.** Running your own agent on your own
subscription is fine. Serving other people's traffic through one token is not,
and you would hit the rate limit in seconds anyway. Anything with users wants
an API key with Console credit.
"""

import asyncio
import contextlib
import os
from typing import Optional

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions,
                              ResultMessage, TextBlock, ToolUseBlock,
                              create_sdk_mcp_server, query, tool)

from eleph import Ungrounded

SERVER = "suporte"
DEFAULT_MODEL = "claude-opus-5"


@contextlib.contextmanager
def _without_api_key():
    """The pitfall, handled. An API key in the environment outranks the OAuth
    session, so it has to be out of the way for the plan to be used at all."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def _text(body: str) -> dict:
    return {"content": [{"type": "text", "text": body}]}


def make_server(backend, guard=None, refusals=None, caller=None):
    """The same three tools, and the same one difference.

    `refusals` is a list the tools append to when the guard turns an operation
    down, so the harness can count them at the source instead of inferring
    them from what did not happen.
    """
    refusals = refusals if refusals is not None else []

    def blocked(user):
        """Whether this caller may speak about this account at all. The caller
        comes from the session, never from the conversation: the model is not
        asked who it is speaking for, so it cannot answer wrongly."""
        if guard is None:
            return None
        try:
            guard.require("autorizado", caller, user)
        except Ungrounded:
            refusals.append("autorizado")
            return _text(f"RECUSADO pela politica: quem esta na linha nao se "
                         f"autenticou na conta de {user}. Nao confirme nem "
                         f"negue nada sobre essa conta.")
        return None

    @tool("consultar_conta",
          "Consulta a conta de um cliente: se esta ativa e quais cobrancas tem.",
          {"user": str})
    async def consultar_conta(args):
        return blocked(args["user"]) or _text(str(backend.lookup(args["user"])))

    @tool("cancelar_assinatura", "Cancela a assinatura de um cliente.",
          {"user": str})
    async def cancelar_assinatura(args):
        user = args["user"]
        if (stop := blocked(user)) is not None:
            return stop
        if guard is not None:
            try:
                guard.require("active", user)
            except Ungrounded:
                refusals.append("cancelar_assinatura")
                return _text("RECUSADO pela politica: o registro nao mostra "
                             f"assinatura ativa para {user}, entao nao ha o "
                             "que cancelar.")
        out = backend.cancel(user)
        if guard is not None:
            guard.record("cancelled", user)
        return _text(out)

    @tool("encaminhar_para_supervisao",
          "Encaminha uma cobranca acima da sua alcada para a supervisao.",
          {"user": str, "charge_id": str})
    async def encaminhar_para_supervisao(args):
        user, charge_id = args["user"], args["charge_id"]
        if (stop := blocked(user)) is not None:
            return stop
        out = backend.escalate(user, charge_id)
        if guard is not None:
            guard.record("escalated", user, charge_id)
        return _text(out)

    @tool("emitir_reembolso",
          "Emite o reembolso de uma cobranca especifica de um cliente.",
          {"user": str, "charge_id": str})
    async def emitir_reembolso(args):
        user, charge_id = args["user"], args["charge_id"]
        if (stop := blocked(user)) is not None:
            return stop
        if guard is not None:
            try:
                guard.require("may_refund", user, charge_id)
            except Ungrounded:
                refusals.append("emitir_reembolso")
                return _text(
                    f"RECUSADO pela politica: a cobranca {charge_id} de "
                    f"{user} nao pode ser reembolsada por voce. Vale para "
                    "cobranca em aberto de cliente que ja cancelou, ate "
                    "R$ 200. Acima disso, encaminhe para a supervisao.")
        out = backend.refund(user, charge_id)
        if guard is not None:
            guard.record("refunded", user, charge_id)
            guard.promise(user, "settled_back", user, charge_id,
                          before=("statement_closed", (user,)))
        return _text(out)

    return create_sdk_mcp_server(
        name=SERVER, tools=[consultar_conta, cancelar_assinatura,
                            emitir_reembolso, encaminhar_para_supervisao])


def _options(server, system_prompt: str, model: str) -> ClaudeAgentOptions:
    names = [f"mcp__{SERVER}__{t}" for t in
             ("consultar_conta", "cancelar_assinatura", "emitir_reembolso",
              "encaminhar_para_supervisao")]
    return ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,
        mcp_servers={SERVER: server},
        allowed_tools=names,
        # nothing but our three tools: no file access, no shell, no web
        disallowed_tools=["Bash", "Read", "Write", "Edit", "WebSearch",
                          "WebFetch", "Glob", "Grep", "Task", "ToolSearch",
                          "NotebookEdit", "TodoWrite"],
        permission_mode="bypassPermissions",
        setting_sources=None,          # ignore any local project settings
        max_turns=8,
    )


async def _ask(backend, guard, system_prompt, message, model, caller) -> dict:
    refusals = []
    server = make_server(backend, guard, refusals, caller)
    calls, replies, cost = [], [], None
    with _without_api_key():
        # aclosing, not a bare async for: letting the loop shut down with the
        # SDK generator still open raises during cleanup, and the exception
        # surfaces inside the *next* asyncio.run, which is a miserable way to
        # lose a run in a comparison harness
        async with contextlib.aclosing(
                query(prompt=message,
                      options=_options(server, system_prompt,
                                       model))) as stream:
            async for msg in stream:
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, ToolUseBlock):
                            calls.append(
                                block.name.replace(f"mcp__{SERVER}__", ""))
                        elif isinstance(block, TextBlock):
                            replies.append(block.text)
                elif isinstance(msg, ResultMessage):
                    cost = getattr(msg, "total_cost_usd", None)
    return {"calls": calls, "reply": replies[-1] if replies else "",
            "refusals": len(refusals), "cost": cost}


def ask(backend, guard, system_prompt: str, message: str,
        model: Optional[str] = None, caller: Optional[str] = None) -> dict:
    """One turn against the plan. Synchronous, for the comparison harness."""
    return asyncio.run(_ask(backend, guard, system_prompt, message,
                            model or DEFAULT_MODEL, caller))
