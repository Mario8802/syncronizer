# Syncronizer 🔄

A Python tool that synchronizes a source folder with a replica folder.

## ✨ Features
- One-way sync from source → replica
- Detects file changes via MD5 hash comparison
- Logs all file operations (copy, update, delete)
- Supports nested directories
- Interval-based repeated sync

## 🧪 Usage

```bash
python sync.py <source_folder> <replica_folder> <sync_interval> <log_file>
