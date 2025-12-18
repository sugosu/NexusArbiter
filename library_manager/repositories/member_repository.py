from storage.json_storage import JsonStorage
from typing import Optional, Dict, Any, List


class MemberRepository:
    def __init__(self, storage: JsonStorage) -> None:
        self._storage = storage

    def find(self, member_id: str, storage_path: str) -> Optional[Dict[str, Any]]:
        raw = self._storage.read(storage_path)
        if isinstance(raw, list):
            for record in raw:
                if isinstance(record, dict) and record.get("id") == member_id:
                    return record
            return None
        if isinstance(raw, dict):
            if raw.get("id") == member_id:
                return raw
            if "members" in raw and isinstance(raw["members"], list):
                for record in raw["members"]:
                    if isinstance(record, dict) and record.get("id") == member_id:
                        return record
            for value in raw.values():
                if isinstance(value, list):
                    for record in value:
                        if isinstance(record, dict) and record.get("id") == member_id:
                            return record
        return None

    def update(self, member: Dict[str, Any], storage_path: str) -> None:
        raw = self._storage.read(storage_path)
        member_id = member.get("id")
        if isinstance(raw, list):
            updated = list(raw)
            for i, record in enumerate(updated):
                if isinstance(record, dict) and record.get("id") == member_id:
                    updated[i] = member
                    break
            else:
                updated.append(member)
            self._storage.write(storage_path, updated)
            return
        if isinstance(raw, dict):
            if raw.get("id") == member_id:
                self._storage.write(storage_path, member)
                return
            if "members" in raw and isinstance(raw["members"], list):
                updated_list = list(raw["members"])
                for i, record in enumerate(updated_list):
                    if isinstance(record, dict) and record.get("id") == member_id:
                        updated_list[i] = member
                        break
                else:
                    updated_list.append(member)
                new_raw = dict(raw)
                new_raw["members"] = updated_list
                self._storage.write(storage_path, new_raw)
                return
            for key, value in raw.items():
                if isinstance(value, list):
                    updated_list = list(value)
                    for i, record in enumerate(updated_list):
                        if isinstance(record, dict) and record.get("id") == member_id:
                            updated_list[i] = member
                            break
                    else:
                        updated_list.append(member)
                    new_raw = dict(raw)
                    new_raw[key] = updated_list
                    self._storage.write(storage_path, new_raw)
                    return
        self._storage.write(storage_path, [member])
