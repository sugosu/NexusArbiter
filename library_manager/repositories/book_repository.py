from storage.json_storage import JsonStorage
from typing import Optional, Dict, Any, List


class BookRepository:
    def __init__(self, storage: JsonStorage) -> None:
        self._storage = storage

    def find(self, book_id: str, storage_path: str) -> Optional[Dict[str, Any]]:
        raw = self._storage.read(storage_path)
        records: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            records = raw
        elif isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, list):
                    records = v
                    break
        for record in records:
            try:
                if record.get("id") == book_id:
                    return record
            except Exception:
                continue
        return None

    def update(self, book: Dict[str, Any], storage_path: str) -> None:
        raw = self._storage.read(storage_path)
        records: List[Dict[str, Any]] = []
        container_is_list = False
        container_key: Optional[str] = None
        if isinstance(raw, list):
            records = raw.copy()
            container_is_list = True
        elif isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, list):
                    records = v.copy()
                    container_key = k
                    break
        updated = False
        for idx, record in enumerate(records):
            try:
                if record.get("id") == book.get("id"):
                    records[idx] = book
                    updated = True
                    break
            except Exception:
                continue
        if not updated:
            records.append(book)
        if container_is_list:
            updated_data: Any = records
        elif isinstance(raw, dict) and container_key is not None:
            new_raw = dict(raw)
            new_raw[container_key] = records
            updated_data = new_raw
        else:
            updated_data = records
        self._storage.write(storage_path, updated_data)
