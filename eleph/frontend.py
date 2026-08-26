"""The boundary between fluent language and binding commitment.

McCarthy could not cross this in 1998: mapping what a person actually says
onto a typed speech act was the open problem. It is no longer, and that is
most of why the language is buildable now.

The architecture puts the model *outside* the verified core on purpose. An
extractor only ever proposes a speech act. What happens next is the program's
business, and the answer axiom still holds: if acting on the proposal would
require the program to say something the log does not support, the runtime
refuses. The fluent part is untrusted, and the part that can commit you is not.

Note what constrains the model here: the JSON schema is generated from the
program's own declarations, so a subject the program does not handle is not
merely rejected downstream -- it is not expressible in the reply.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from . import ast as A


@dataclass(frozen=True)
class SpeechAct:
    performative: str          # question | request
    speaker: str
    subject: str
    args: tuple

    def __str__(self):
        return f"{self.performative} {self.subject}({', '.join(self.args)})"


def addressable(prog: A.Program):
    """What this program can actually be spoken to about."""
    return sorted({(h.performative, h.subject.name) for h in prog.handlers})


def arity_of(prog: A.Program, subject: str) -> int:
    decl = prog.event(subject) or prog.fact(subject)
    return len(decl.params) if decl else 0


def schema_for(prog: A.Program) -> dict:
    """A JSON schema that admits exactly the utterances this program handles."""
    subjects = sorted({s for _, s in addressable(prog)})
    performatives = sorted({p for p, _ in addressable(prog)})
    return {
        "type": "object",
        "properties": {
            "understood": {
                "type": "boolean",
                "description": "false if the utterance is not one of the "
                               "speech acts this program handles",
            },
            "performative": {"type": "string", "enum": performatives},
            "subject": {"type": "string", "enum": subjects},
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "the named things the utterance is about, in "
                               "the order the subject declares them",
            },
        },
        "required": ["understood", "performative", "subject", "args"],
        "additionalProperties": False,
    }


class Extractor(Protocol):
    def extract(self, text: str, speaker: str,
                prog: A.Program) -> Optional[SpeechAct]:
        ...


# ------------------------------------------------------------------ offline

class PatternExtractor:
    """A deliberately crude extractor, so the demo runs with no network.

    It is meant to be beatable. Its mistakes are the point: whatever it gets
    wrong, the language still will not let the program lie about it.
    """

    ASKING = ("?", "tenho", "tem ", "qual", "quantos", "quantas", "sera")

    def __init__(self, roster: List[str] = ()):
        self.roster = list(roster)

    def extract(self, text, speaker, prog) -> Optional[SpeechAct]:
        low = text.lower()
        want = "question" if any(m in low for m in self.ASKING) else "request"

        subject = None
        for perf, name in addressable(prog):
            if perf != want:
                continue
            if name in low or name.replace("_", " ") in low:
                subject = name
                break
        if subject is None:
            return None

        known = set(self.roster) | {speaker}
        args = [w.strip(".,!?") for w in text.split()
                if w.strip(".,!?") in known]
        seen, ordered = set(), []
        for a in args:
            if a not in seen:
                seen.add(a)
                ordered.append(a)

        need = arity_of(prog, subject)
        if len(ordered) < need:
            ordered += [speaker] * (need - len(ordered))
        return SpeechAct(want, speaker, subject, tuple(ordered[:need]))


# ------------------------------------------------------------------- Claude

class ClaudeExtractor:
    """Claude reads the utterance; the schema comes from the program.

    The model is asked only to name a speech act. It never decides what is
    true, never composes an answer, and cannot invent a subject -- the enum
    is built from the program's own handlers.
    """

    MODEL = "claude-opus-5"

    SYSTEM = (
        "You map a person's utterance onto exactly one speech act that a "
        "program declares it can handle. You are a translator at a boundary, "
        "not a participant: never decide whether anything is true, never "
        "answer the question, never invent a subject or a name. If the "
        "utterance is not one of the available speech acts, set understood "
        "to false. Argument order must follow the subject's declaration."
    )

    def __init__(self, client=None, roster: List[str] = ()):
        self.client = client
        self.roster = list(roster)

    def _connect(self):
        if self.client is None:
            import anthropic                     # optional dependency
            self.client = anthropic.Anthropic()
        return self.client

    def prompt(self, text, speaker, prog) -> str:
        lines = ["Atos de fala que este programa aceita:"]
        for perf, name in addressable(prog):
            decl = prog.event(name) or prog.fact(name)
            params = ", ".join(f"{p.name}: {p.sort}" for p in decl.params) \
                if decl else ""
            lines.append(f"  {perf} {name}({params})")
        if self.roster:
            lines.append("\nNomes conhecidos: " + ", ".join(self.roster))
        lines.append(f"\nQuem fala: {speaker}")
        lines.append(f"Enunciado: {text}")
        return "\n".join(lines)

    def extract(self, text, speaker, prog) -> Optional[SpeechAct]:
        import json
        client = self._connect()
        response = client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=self.SYSTEM,
            messages=[{"role": "user",
                       "content": self.prompt(text, speaker, prog)}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": schema_for(prog)},
            },
        )
        payload = next(b.text for b in response.content if b.type == "text")
        data = json.loads(payload)
        if not data.get("understood"):
            return None
        args = tuple(data["args"])[:arity_of(prog, data["subject"])]
        return SpeechAct(data["performative"], speaker, data["subject"], args)


# ------------------------------------------------------------------- bridge

def interpret(machine, extractor: Extractor, text: str, speaker: str):
    """Propose, then let the language dispose.

    Returns the speech act that was actually delivered, or None if nothing
    the program handles was recognised. Any Refusal raised downstream is left
    to propagate: a refusal is the system working.
    """
    act = extractor.extract(text, speaker, machine.prog)
    if act is None:
        machine.say(f"{speaker}: {text}")
        machine.say("    (nada que este programa saiba tratar)")
        return None
    machine.say(f"{speaker}: \"{text}\"")
    machine.say(f"    -> lido como: {act}")
    machine.deliver(act.performative, speaker, act.subject, act.args)
    return act
