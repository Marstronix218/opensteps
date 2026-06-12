"""The opensteps command: keygen, wrap, verify."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from opensteps import __version__


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="opensteps",
        description=(
            "Signed, hash-chained, independently verifiable receipts for AI agent "
            "tool calls."
        ),
    )
    parser.add_argument("--version", action="version", version=f"opensteps {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_keygen = sub.add_parser("keygen", help="generate an Ed25519 signing keypair")
    p_keygen.add_argument("--out-dir", required=True, type=Path)

    p_wrap = sub.add_parser(
        "wrap",
        help="run an MCP server behind the receipt-writing policy proxy",
        usage=(
            "opensteps wrap --policy POLICY --key KEY --log LOG "
            "[--agent-id ID] [--framework F] [--server-name NAME] "
            "[--approval-timeout SECS] -- COMMAND [ARGS...]"
        ),
    )
    p_wrap.add_argument("--policy", required=True, type=Path)
    p_wrap.add_argument("--key", required=True, type=Path, help="Ed25519 private key (PEM)")
    p_wrap.add_argument("--log", required=True, type=Path, help="receipt chain (JSONL, appended)")
    p_wrap.add_argument("--agent-id", default="agent")
    p_wrap.add_argument("--framework", default="mcp")
    p_wrap.add_argument("--server-name", default=None,
                        help="server name recorded in receipts (default: command basename)")
    p_wrap.add_argument("--approval-timeout", type=float, default=120.0)
    p_wrap.add_argument("server_cmd", nargs=argparse.REMAINDER,
                        help="the wrapped MCP server command, after --")

    p_verify = sub.add_parser(
        "verify", help="verify a receipt chain offline (no network, no account)"
    )
    p_verify.add_argument("chain", type=Path, help="receipt chain (JSONL) or single receipt")
    p_verify.add_argument("--pubkey", required=True, type=Path)
    p_verify.add_argument("--single", action="store_true",
                          help="verify one receipt's signature only (no chain checks)")
    p_verify.add_argument("--quiet", action="store_true", help="exit code only")

    args = parser.parse_args(argv)
    if args.command == "keygen":
        return _cmd_keygen(args)
    if args.command == "wrap":
        return _cmd_wrap(args)
    if args.command == "verify":
        return _cmd_verify(args)
    return 2


def _cmd_keygen(args) -> int:
    from opensteps.keys import generate_keypair

    priv_path, pub_path = generate_keypair(args.out_dir)
    print(f"private key: {priv_path}  (keep this on the signing host only)")
    print(f"public key:  {pub_path}  (share with anyone who should verify receipts)")
    return 0


def _cmd_wrap(args) -> int:
    from opensteps.keys import load_private_key
    from opensteps.policy import Policy
    from opensteps.proxy import run_proxy
    from opensteps.receipts import ChainWriter

    cmd = args.server_cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("opensteps wrap: missing server command after --", file=sys.stderr)
        return 2

    policy = Policy.load(args.policy)
    private_key = load_private_key(args.key)
    server_name = args.server_name or os.path.basename(cmd[0])
    writer = ChainWriter(
        args.log,
        private_key,
        agent_id=args.agent_id,
        framework=args.framework,
        server_name=server_name,
    )
    return asyncio.run(
        run_proxy(cmd, policy, writer, server_name,
                  approval_timeout=args.approval_timeout)
    )


def _cmd_verify(args) -> int:
    import json

    from opensteps.keys import load_public_key
    from opensteps.verify import verify_chain, verify_receipt

    public_key = load_public_key(args.pubkey)

    if args.single:
        receipt = json.loads(args.chain.read_text(encoding="utf-8"))
        ok, reason = verify_receipt(receipt, public_key)
        if not args.quiet:
            mark = "✓ VALID  " if ok else "✗ INVALID"
            print(f"{mark} {args.chain} — {reason}")
        return 0 if ok else 1

    result = verify_chain(args.chain, public_key)
    if not args.quiet:
        if result.valid:
            print(
                f"✓ VALID   {args.chain} — {result.receipts_checked} receipts, "
                "chain intact, all signatures verify"
            )
            print(f"  chain head: {result.head_hash}")
        else:
            where = (
                f"receipt {result.error_index}"
                + (f" ({result.error_receipt_id})" if result.error_receipt_id else "")
                if result.error_index is not None
                else "chain"
            )
            print(f"✗ INVALID {args.chain} — {where}: {result.error_reason}")
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
