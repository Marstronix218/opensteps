"""MCP stdio proxy: transparent JSON-RPC passthrough with receipts.

The proxy spawns the wrapped MCP server and relays newline-delimited JSON-RPC
in both directions. Only `tools/call` requests are intercepted:

  allow   -> forwarded; a receipt is written when the response arrives
  deny    -> never reaches the server; the agent gets a tool error naming the
             rule, and the *blocked attempt* becomes a receipt
  approve -> a human answers on /dev/tty; rejection behaves like deny but
             records the approver's decision

Everything else — initialize, tools/list, notifications, server-initiated
requests — is forwarded verbatim, so the proxy stays MCP-version- and
framework-agnostic. Client messages are processed sequentially; an approval
prompt intentionally pauses the pipeline.
"""

import asyncio
import json
import sys
from dataclasses import dataclass

from opensteps.approval import request_approval
from opensteps.canonical import hash_json
from opensteps.policy import Policy
from opensteps.receipts import ChainWriter


@dataclass
class PendingCall:
    tool: str
    request_hash: str
    rule_id: str
    decision: str
    approver_id: str | None = None
    approver_method: str = "none"
    approver_decision: str | None = None


class MCPProxy:
    def __init__(
        self,
        server_cmd: list[str],
        policy: Policy,
        chain_writer: ChainWriter,
        server_name: str,
        approval_fn=request_approval,
        approval_timeout: float = 120.0,
    ):
        self.server_cmd = server_cmd
        self.policy = policy
        self.chain = chain_writer
        self.server_name = server_name
        self.approval_fn = approval_fn
        self.approval_timeout = approval_timeout
        self._pending: dict[object, PendingCall] = {}
        self._chain_lock = asyncio.Lock()
        self._client_writer: asyncio.StreamWriter | None = None
        self._proc: asyncio.subprocess.Process | None = None

    async def run(self) -> int:
        self._proc = await asyncio.create_subprocess_exec(
            *self.server_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # inherit: wrapped server's stderr stays visible
        )
        client_reader, self._client_writer = await _stdio_streams()

        to_server = asyncio.create_task(self._pump_client_to_server(client_reader))
        to_client = asyncio.create_task(self._pump_server_to_client())
        await asyncio.wait(
            [to_server, to_client], return_when=asyncio.FIRST_COMPLETED
        )

        # Client hung up or server exited: close the server's stdin and drain.
        if self._proc.stdin and not self._proc.stdin.is_closing():
            self._proc.stdin.close()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._proc.terminate()
            await self._proc.wait()
        for task in (to_server, to_client):
            task.cancel()
        return self._proc.returncode or 0

    async def _pump_client_to_server(self, client_reader: asyncio.StreamReader):
        while True:
            line = await client_reader.readline()
            if not line:
                break
            if not line.strip():
                continue
            await self._handle_client_line(line)

    async def _pump_server_to_client(self):
        assert self._proc and self._proc.stdout
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                break
            if not line.strip():
                continue
            await self._handle_server_line(line)

    async def _handle_client_line(self, raw: bytes):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._write_server(raw)
            return
        if (
            isinstance(msg, dict)
            and msg.get("method") == "tools/call"
            and "id" in msg
        ):
            await self._handle_tool_call(msg, raw)
        else:
            await self._write_server(raw)

    async def _handle_tool_call(self, msg: dict, raw: bytes):
        params = msg.get("params") or {}
        tool = params.get("name", "")
        arguments = params.get("arguments") or {}
        request_hash = hash_json(params)
        decision = self.policy.evaluate(self.server_name, tool, arguments)

        if decision.action == "allow":
            self._pending[msg["id"]] = PendingCall(
                tool=tool,
                request_hash=request_hash,
                rule_id=decision.rule_id,
                decision="allow",
            )
            await self._write_server(raw)
            return

        if decision.action == "approve":
            approval = await asyncio.to_thread(
                self.approval_fn,
                self.server_name,
                tool,
                arguments,
                decision.rule_id,
                self.approval_timeout,
            )
            if approval.approved:
                self._pending[msg["id"]] = PendingCall(
                    tool=tool,
                    request_hash=request_hash,
                    rule_id=decision.rule_id,
                    decision="approve",
                    approver_id=approval.approver_id,
                    approver_method=approval.method,
                    approver_decision="approved",
                )
                await self._write_server(raw)
            else:
                await self._record_and_block(
                    msg,
                    tool,
                    request_hash,
                    decision.rule_id,
                    "approve",
                    approver_id=approval.approver_id,
                    approver_method=approval.method,
                    approver_decision="rejected",
                    reason=f"rejected by approver under rule '{decision.rule_id}'",
                )
            return

        await self._record_and_block(
            msg,
            tool,
            request_hash,
            decision.rule_id,
            "deny",
            reason=f"blocked by policy rule '{decision.rule_id}'",
        )

    async def _record_and_block(
        self,
        msg: dict,
        tool: str,
        request_hash: str,
        rule_id: str,
        decision: str,
        *,
        reason: str,
        approver_id: str | None = None,
        approver_method: str = "none",
        approver_decision: str | None = None,
    ):
        async with self._chain_lock:
            self.chain.append(
                tool=tool,
                request_hash=request_hash,
                response_hash=None,
                rule_id=rule_id,
                decision=decision,
                approver_id=approver_id,
                approver_method=approver_method,
                approver_decision=approver_decision,
            )
        response = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "content": [{"type": "text", "text": f"OpenSteps: {reason}"}],
                "isError": True,
            },
        }
        await self._write_client(
            (json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8")
        )

    async def _handle_server_line(self, raw: bytes):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._write_client(raw)
            return
        if (
            isinstance(msg, dict)
            and "method" not in msg  # a response, not a server-initiated request
            and msg.get("id") in self._pending
            and ("result" in msg or "error" in msg)
        ):
            call = self._pending.pop(msg["id"])
            response_hash = hash_json(
                msg["result"] if "result" in msg else msg["error"]
            )
            async with self._chain_lock:
                self.chain.append(
                    tool=call.tool,
                    request_hash=call.request_hash,
                    response_hash=response_hash,
                    rule_id=call.rule_id,
                    decision=call.decision,
                    approver_id=call.approver_id,
                    approver_method=call.approver_method,
                    approver_decision=call.approver_decision,
                )
        await self._write_client(raw)

    async def _write_server(self, raw: bytes):
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(raw if raw.endswith(b"\n") else raw + b"\n")
        await self._proc.stdin.drain()

    async def _write_client(self, raw: bytes):
        assert self._client_writer
        self._client_writer.write(raw if raw.endswith(b"\n") else raw + b"\n")
        await self._client_writer.drain()


async def _stdio_streams() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), sys.stdin
    )
    w_transport, w_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, None, loop)
    return reader, writer


async def run_proxy(
    server_cmd: list[str],
    policy: Policy,
    chain_writer: ChainWriter,
    server_name: str,
    approval_timeout: float = 120.0,
) -> int:
    proxy = MCPProxy(
        server_cmd,
        policy,
        chain_writer,
        server_name,
        approval_timeout=approval_timeout,
    )
    return await proxy.run()
