"""A stand in for the model, so the plumbing runs with no key and no spend.

Read this for what it is. It is **not evidence about how Claude behaves**. It
is one fixed, plausible agent policy: look up the account, then do what the
customer asked for. Plenty of real agents behave exactly like that, and it is
the behaviour the guard is meant to catch, but a scripted model cannot tell you
how often a real one does it.

For that, set ANTHROPIC_API_KEY and run `python compare.py --live`.

The same script drives both halves of the comparison, which is the point: any
difference in outcome comes from the guard, not from the model.
"""

import re
from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

USER = re.compile(r"\b(?:cliente|usuario|conta)[: ]+([a-z_]+)", re.I)
CHARGE = re.compile(r"\b(c\d+)\b", re.I)
WANTS_REFUND = re.compile(r"quero o? ?reembolso|estorn|devolv", re.I)
# A request, not a claim about the past: "quero cancelar" is an instruction,
# "eu cancelei mes passado" is an assertion about history, and the two must not
# be confused. Confusing them is a defect in this stand in, not a finding.
WANTS_CANCEL = re.compile(
    r"quero cancelar|pode cancelar|cancele |cancelar minha|favor cancelar",
    re.I)


class ScriptedModel(BaseChatModel):
    """Looks the account up, then does what was asked. Nothing more."""

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        """The script is fixed, so the tool list changes nothing here.

        It still has to be accepted: the agent binds tools before every call,
        and a stand in that refused would not be running the same code path
        the real model runs.
        """
        return self

    def _generate(self, messages: List[BaseMessage],
                  stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None,
                  **kwargs: Any) -> ChatResult:
        asked = next((m.content for m in messages
                      if getattr(m, "type", "") == "human"), "")
        called = [c["name"] for m in messages
                  for c in (getattr(m, "tool_calls", None) or [])]
        results = [m.content for m in messages
                   if getattr(m, "type", "") == "tool"]

        user = (USER.search(asked).group(1) if USER.search(asked) else "?")
        charge = (CHARGE.search(asked).group(1).lower()
                  if CHARGE.search(asked) else "c1")

        def call(name, args):
            return self._wrap(AIMessage(
                content="", tool_calls=[{"name": name, "args": args,
                                         "id": f"call_{len(called)}"}]))

        if "consultar_conta" not in called:
            return call("consultar_conta", {"user": user})

        if WANTS_REFUND.search(asked) and "emitir_reembolso" not in called:
            return call("emitir_reembolso", {"user": user,
                                             "charge_id": charge})

        if WANTS_CANCEL.search(asked) and "cancelar_assinatura" not in called:
            return call("cancelar_assinatura", {"user": user})

        last = results[-1] if results else ""
        if "RECUSADO" in last:
            return self._wrap(AIMessage(
                content="Verifiquei o registro e a operacao nao se aplica ao "
                        "seu caso. " + last.split("politica:")[-1].strip()))
        return self._wrap(AIMessage(content=f"Pronto. {last}"))

    @staticmethod
    def _wrap(message: AIMessage) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=message)])
