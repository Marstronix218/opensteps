"""Human approval prompt (v0: CLI).

The MCP transport owns the proxy's stdin/stdout, so the prompt talks to the
controlling terminal (/dev/tty) directly. Anything other than an explicit
"y"/"yes" — including no terminal, timeout, or EOF — is a rejection: approval
must fail closed.
"""

import getpass
import json
import select
from dataclasses import dataclass

DEFAULT_TIMEOUT = 120.0


@dataclass
class ApprovalResult:
    approved: bool
    approver_id: str | None
    method: str  # "cli" when a human answered (or timed out at a tty), "none" when no tty


def prompt_for_approval(summary: str, in_stream, out_stream,
                        timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Show the summary, read y/N from in_stream. Streams are injectable for tests."""
    out_stream.write(
        "\n[OpenSteps] approval required\n"
        f"{summary}\n"
        f"Approve? [y/N] (auto-reject in {timeout:.0f}s): "
    )
    out_stream.flush()

    try:
        fd = in_stream.fileno()  # StringIO raises io.UnsupportedOperation (an OSError)
    except (OSError, AttributeError):
        fd = None

    if fd is not None:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            out_stream.write("\n[OpenSteps] no answer — rejected\n")
            out_stream.flush()
            return False

    answer = in_stream.readline().strip().lower()
    return answer in ("y", "yes")


def request_approval(server: str, tool: str, arguments: dict, rule_id: str,
                     timeout: float = DEFAULT_TIMEOUT) -> ApprovalResult:
    """Open /dev/tty and ask a human. No tty -> rejected with method 'none'."""
    summary = (
        f"  rule:   {rule_id}\n"
        f"  server: {server}\n"
        f"  tool:   {tool}\n"
        f"  args:   {json.dumps(arguments, ensure_ascii=False, sort_keys=True)}"
    )
    try:
        tty_in = open("/dev/tty", "r")
        tty_out = open("/dev/tty", "w")
    except OSError:
        return ApprovalResult(approved=False, approver_id=None, method="none")

    with tty_in, tty_out:
        approved = prompt_for_approval(summary, tty_in, tty_out, timeout=timeout)
    return ApprovalResult(
        approved=approved, approver_id=getpass.getuser(), method="cli"
    )
