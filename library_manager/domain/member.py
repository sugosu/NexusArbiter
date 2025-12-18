from typing import Dict, Any


class Member:
    def __init__(self, id: str, name: str, loan_limit: int, current_loans: int = 0) -> None:
        self.id = id
        self.name = name
        self.loan_limit = loan_limit
        self.current_loans = current_loans

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "loan_limit": self.loan_limit,
            "current_loans": self.current_loans,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Member":
        return Member(
            id=data["id"],
            name=data["name"],
            loan_limit=data.get("loan_limit", 0),
            current_loans=data.get("current_loans", 0),
        )
