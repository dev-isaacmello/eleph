"""eleph -- a language whose programs cannot lie.

Isaac Mello, 2026. Implements and extends Elephant 2000, specified by John
McCarthy (Stanford, 6 November 1998) and never implemented by him.

For embedding in a Python system, start with `Policy`:

    from eleph import Policy
    policy = Policy.from_file("booking.eleph")
    assert policy.verify().proved
    g = policy.guard(log="booking.jsonl")
"""

from importlib.metadata import PackageNotFoundError, version as _version

from .guard import Guard, Policy, Ungrounded, UnknownName, VerifyReport
from .runtime import Commitment, Event, Machine, NotPermitted, Refusal
from .store import Store

__all__ = ["Policy", "Guard", "VerifyReport", "Ungrounded", "UnknownName",
           "Commitment", "Event", "Machine", "NotPermitted", "Refusal",
           "Store"]
try:
    # One source of truth, and it is pyproject.toml. A version repeated in two
    # files is a version that will eventually disagree with itself, quietly,
    # in a release.
    __version__ = _version("eleph")
except PackageNotFoundError:            # running from a checkout, not installed
    __version__ = "0.0.0+unknown"
