"""
Synchronizes a source folder with a replica, performs one-way synchronization with MD5-based comparison,
supports nested directories, logs all operations, and handles incorrect inputs gracefully.
"""

import hashlib
import shutil
import logging
import time
import sys
from pathlib import Path


# LoggerFactory configures a logger that logs to both a file and the console
class LoggerFactory:
    @staticmethod
    def create_logger(log_path: Path) -> logging.Logger:
        # Ensure the log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("FolderSyncLogger")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger


# MD5ComparisonStrategy uses md5 hashes to determine if files differ
class MD5ComparisonStrategy:
    @staticmethod
    def files_are_different(file1: Path, file2: Path) -> bool:
        try:
            return MD5ComparisonStrategy._calculate_md5(file1) != MD5ComparisonStrategy._calculate_md5(file2)
        except Exception as e:
            logger = logging.getLogger("FolderSyncLogger")
            logger.warning(f"⚠ Failed to compare files: {file1} and {file2} due to error: {e}")
            return True  # Treat as different if comparison fails


    @staticmethod
    def _calculate_md5(file_path: Path) -> str:
        # Efficiently compute md5 hash by reading file in chunks
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


# FolderSynchronizer handles syncing logic between source and replica directories
class FolderSynchronizer:
    def __init__(self, source: Path, replica: Path, logger: logging.Logger, comparison_strategy):
        self.source = source
        self.replica = replica
        self.logger = logger
        self.comparison_strategy = comparison_strategy

    def synchronize(self):
        self._sync_files()
        self._remove_extra_files()

    def _sync_files(self):
        for src_file in self.source.rglob("*"):
            relative_path = src_file.relative_to(self.source)
            replica_file = self.replica / relative_path

            # Skip symbolic links to avoid potential security risks
            if src_file.is_symlink():
                self.logger.warning(f"Skipped symlink: {relative_path}")
                continue

            try:
                if src_file.is_dir():
                    # Create directory if it doesn't exist in replica
                    replica_file.mkdir(parents=True, exist_ok=True)
                else:
                    # Copy or update file if it’s missing or has changed
                    if not replica_file.exists() or self.comparison_strategy.files_are_different(src_file, replica_file):
                        replica_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, replica_file)
                        self.logger.info(f"Copied/Updated: {relative_path}")
            except Exception as e:
                self.logger.error(f"Error processing {relative_path}: {e}")

    def _remove_extra_files(self):
        for replica_file in self.replica.rglob("*"):
            relative_path = replica_file.relative_to(self.replica)
            src_file = self.source / relative_path

            # Remove file or folder from replica if it doesn't exist in source
            if not src_file.exists():
                try:
                    if replica_file.is_file():
                        replica_file.unlink()
                        self.logger.info(f"Deleted file: {relative_path}")
                    elif replica_file.is_dir():
                        shutil.rmtree(replica_file)
                        self.logger.info(f"Deleted folder: {relative_path}")
                except Exception as e:
                    self.logger.error(f"Error deleting {relative_path}: {e}")


# Entry point for the script – parses arguments and triggers synchronization
def main():
    if len(sys.argv) != 6:
        print("Usage: python sync.py <source> <replica> <interval> <count> <logfile>")
        return

    try:
        source = Path(sys.argv[1])
        replica = Path(sys.argv[2])
        interval = int(sys.argv[3])
        count = int(sys.argv[4])
        log_file = Path(sys.argv[5])

        # Safety checks: avoid root paths and syncing a folder with itself
        if source == Path("/") or replica == Path("/") or source.resolve() == replica.resolve():
            print("Error: Source and replica must not be the same path or the root directory.")
            return

        # Prevent syncing into a subdirectory of the source
        try:
            replica.resolve().relative_to(source.resolve())
            print("Error: Replica cannot be a subdirectory of the source.")
            return
        except ValueError:
            pass

        if interval <= 0 or count <= 0:
            print("Error: Interval and count must be positive integers.")
            return

        if not source.exists() or not source.is_dir():
            print(f"Error: Source path '{source}' does not exist or is not a directory.")
            return

        # Ensure replica exists
        replica.mkdir(parents=True, exist_ok=True)

        logger = LoggerFactory.create_logger(log_file)
        comparison_strategy = MD5ComparisonStrategy()
        syncer = FolderSynchronizer(source, replica, logger, comparison_strategy)

        # Perform synchronization at the given interval, limited by count
        for i in range(count):
            logger.info(f"Starting synchronization cycle {i + 1} of {count}")
            syncer.synchronize()
            if i < count - 1:
                time.sleep(interval)

    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
