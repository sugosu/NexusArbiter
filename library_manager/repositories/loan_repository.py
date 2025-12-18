from typing import List, Dict, Any
from storage.json_storage import JsonStorage

class LoanRepository:
    def __init__(self, storage: JsonStorage) -> None:
        self._storage = storage

    def list_active_by_member(self, member_id: str, storage_path: str) -> List[Dict[str, Any]]:
        raw = self._storage.read(storage_path)
        if isinstance(raw, list):
            collection = raw
        elif isinstance(raw, dict):
            loans = raw.get('loans')
            collection = loans if isinstance(loans, list) else []
        else:
            collection = []
        return [r for r in collection if r.get('member_id') == member_id and not r.get('returned', False)]

    def create(self, loan: Dict[str, Any], storage_path: str) -> Dict[str, Any]:
        raw = self._storage.read(storage_path)
        if isinstance(raw, list):
            collection = raw
            is_dict = False
        elif isinstance(raw, dict):
            loans = raw.get('loans')
            if isinstance(loans, list):
                collection = loans
                is_dict = True
                container = raw
            else:
                collection = []
                is_dict = True
                container = raw
        else:
            collection = []
            is_dict = False
        collection.append(loan)
        if is_dict:
            container['loans'] = collection
            self._storage.write(storage_path, container)
        else:
            self._storage.write(storage_path, collection)
        return loan
