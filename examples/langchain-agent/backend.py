"""A subscription backend, of the ordinary kind: it does what it is told.

Nothing here validates a policy, which is the point. This is the system the
agent talks to in both halves of the comparison, unchanged, so any difference
in outcome comes from the guard and not from the backend having been made
smarter on one side.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Charge:
    id: str
    amount: float
    refunded: bool = False


@dataclass
class Account:
    user: str
    active: bool
    charges: List[Charge] = field(default_factory=list)

    def charge(self, cid):
        return next((c for c in self.charges if c.id == cid), None)


@dataclass
class Backend:
    accounts: Dict[str, Account] = field(default_factory=dict)
    operations: List[tuple] = field(default_factory=list)

    def add(self, account: Account):
        self.accounts[account.user] = account
        return self

    # ------------------------------------------------------------- reads
    def lookup(self, user: str) -> dict:
        a = self.accounts.get(user)
        if a is None:
            return {"error": "conta nao encontrada"}
        return {"user": a.user, "active": a.active,
                "charges": [{"id": c.id, "amount": c.amount,
                             "refunded": c.refunded} for c in a.charges]}

    # ------------------------------------------------------------ writes
    def cancel(self, user: str) -> str:
        a = self.accounts.get(user)
        if a is None:
            return "conta nao encontrada"
        a.active = False
        self.operations.append(("cancel", user))
        return f"assinatura de {user} cancelada"

    def refund(self, user: str, charge_id: str) -> str:
        a = self.accounts.get(user)
        if a is None:
            return "conta nao encontrada"
        c = a.charge(charge_id)
        if c is None:
            return "cobranca nao encontrada"
        c.refunded = True
        self.operations.append(("refund", user, charge_id))
        return f"reembolso de R$ {c.amount:.2f} emitido para {user}"

    # ------------------------------------------------------------- state
    def snapshot(self) -> tuple:
        """What actually happened to the data, for comparing against what
        should have happened."""
        return tuple(sorted(
            (u, a.active, tuple(sorted((c.id, c.refunded) for c in a.charges)))
            for u, a in self.accounts.items()))
