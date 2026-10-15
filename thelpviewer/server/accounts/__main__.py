"""Command-line account creation and one-time enrollment invitations."""

import argparse

from .common import AccountError
from .store import AccountStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin-managed THelpViewer accounts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    create = subcommands.add_parser("create", help="Create account and one-time Passkey enrollment token")
    create.add_argument("username")
    create.add_argument("--name", default="")
    invite = subcommands.add_parser("invite", help="Replace an account's enrollment token")
    invite.add_argument("username")
    args = parser.parse_args()
    from ..config import load_config
    from ..storage import prepare_storage
    config = load_config()
    prepare_storage(config)
    store = AccountStore(config.persistent_dir / "development" if config.dev_auto_login else config.persistent_dir)
    try:
        token = (store.create_user(args.username, args.name) if args.command == "create"
                 else store.issue_invitation(args.username))
    except AccountError as error:
        parser.error(str(error))
    print(f"Account: {args.username}\nOne-time enrollment token (24 hours): {token}")
    print("Give this token to the user privately; it will not be shown again.")


if __name__ == "__main__":
    main()
