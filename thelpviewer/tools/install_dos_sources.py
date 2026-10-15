"""Explicitly add configured software to an existing shared C without overwrites."""

from thelpviewer.server.config import load_config
from thelpviewer.server.dos.store import DosPromptStore
from thelpviewer.server.settings import ServerSettings
from thelpviewer.server.storage import prepare_storage


def main() -> None:
    config = load_config()
    prepare_storage(config)
    store = DosPromptStore(config.state_dir / "dos", config.dos_config_path,
        ServerSettings(config.persistent_dir / "server-settings.json"),
        users_dir=config.persistent_dir / "dos" / "users", disk_dir=config.state_dir / "dos" / "c",
        downloads_dir=(config.downloads_dir or config.state_dir / "downloads") / "dos")
    store.prepare(install_sources=True)
    if store.state != "ready":
        raise SystemExit(store.error)
    print(f"DOS C ready: {len(store.files)} files. Restart the server to load its new base.")


if __name__ == "__main__":
    main()
