"""Idle-only expiry and explicit cleanup of downloads and HELP originals."""

import asyncio
import logging
import time

from .cache import clear_download_cache


logger = logging.getLogger(__name__)
CACHE_SWEEP_SECONDS = 3600


class DownloadCache:
    def __init__(self, config, settings, downloads, journal=None):
        self.root = config.downloads_dir or config.state_dir / "downloads"
        self.sources = config.sources_dir or config.state_dir / "sources"
        self.settings, self.downloads = settings, downloads
        self.journal = journal
        self.protected_paths = (config.persistent_dir, config.helps_dir, config.docs_dir,
            config.state_dir / "dos", config.state_dir / "midi", config.state_dir / "backups",
            config.web_dir, config.assets_dir)

    def clear(self, *, expired_only=False) -> dict:
        with self.downloads.maintenance():
            if self.journal and self.journal.pending("content"):
                raise ValueError("Wait for queued or interrupted content jobs before clearing the cache")
            cutoff = time.time() - self.settings.get()["download_cache_days"] * 86400 if expired_only else None
            return clear_download_cache(self.root, protected_paths=self.protected_paths,
                older_than=cutoff, sources_dir=self.sources)

    async def maintain(self):
        while True:
            await asyncio.sleep(CACHE_SWEEP_SECONDS)
            await self.sweep()

    async def sweep(self):
        # Busy pipelines defer cleanup to the next hourly sweep; the maintenance
        # lock also keeps new writers out. Shield/join shutdown's active writer.
        worker = asyncio.create_task(asyncio.to_thread(self.clear, expired_only=True))
        try:
            result = await asyncio.shield(worker)
            if result["files"]:
                logger.info("Expired download cache: removed %s files (%s bytes)", result["files"], result["bytes"])
        except asyncio.CancelledError:
            try:
                await worker
            except (OSError, ValueError):
                pass
            raise
        except (OSError, ValueError) as error:
            logger.warning("Download cache sweep deferred: %s", error)
