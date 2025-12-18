from typing import Dict, Any


class Book:
    def __init__(self, id: str, title: str, author: str, copies_available: int) -> None:
        self.id: str = id
        self.title: str = title
        self.author: str = author
        self.copies_available: int = copies_available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "copies_available": self.copies_available,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Book":
        return Book(
            data.get("id", ""),
            data.get("title", ""),
            data.get("author", ""),
            int(data.get("copies_available", 0)),
        )
