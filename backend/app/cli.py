"""Server-side administration. Run from the backend directory:

    uv run python -m app.cli make-admin you@example.com
    uv run python -m app.cli revoke-admin you@example.com

Admin rights are granted here and nowhere else: no request can grant them, and they
are never inferred from an email address (registration does not verify emails).
"""

import argparse
import asyncio
import sys

from app.core.database import dispose_engine, get_session_factory
from app.repositories.user_repository import UserRepository


async def _set_admin(email: str, value: bool) -> int:
    async with get_session_factory()() as session:
        user = await UserRepository(session).get_by_email(email)
        if user is None:
            print(f"No account with the email {email}.", file=sys.stderr)
            return 1
        user.is_admin = value
        await session.commit()
    print(f"{email} is {'now' if value else 'no longer'} an administrator.")
    return 0


async def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("make-admin", "revoke-admin"):
        commands.add_parser(name).add_argument("email")
    args = parser.parse_args(argv)
    try:
        return await _set_admin(args.email, args.command == "make-admin")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
