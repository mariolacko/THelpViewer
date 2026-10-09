"""Explicitly add configured software to an existing shared C without overwrites."""

from thelpviewer.server.config import load_config
from thelpviewer.server.dos_prompt import DosPromptStore


def main() -> None:
    config = load_config()
    store = DosPromptStore(config.state_dir / "dos", config.dos_config_path)
    store.prepare(install_sources=True)
    if store.state != "ready":
        raise SystemExit(store.error)
    print(f"DOS C ready: {len(store.files)} files. Restart the server to load its new base.")


if __name__ == "__main__":
    main()
