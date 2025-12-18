from typing import Dict, Any, Optional


class Loan:
    def __init__(self, loan_id: str, book_id: str, member_id: str, loan_date: str, due_date: str, returned: bool = False) -> None:
        self.loan_id: str = loan_id
        self.book_id: str = book_id
        self.member_id: str = member_id
        self.loan_date: str = loan_date
        self.due_date: str = due_date
        self.returned: bool = returned

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "book_id": self.book_id,
            "member_id": self.member_id,
            "loan_date": self.loan_date,
            "due_date": self.due_date,
            "returned": self.returned,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Loan":
        return Loan(
            data["loan_id"],
            data["book_id"],
            data["member_id"],
            data["loan_date"],
            data["due_date"],
            data.get("returned", False),
        )
