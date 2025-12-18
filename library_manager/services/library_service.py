from repositories.book_repository import BookRepository
from repositories.member_repository import MemberRepository
from repositories.loan_repository import LoanRepository
from typing import List, Dict, Any, Optional


class LibraryService:
    def __init__(self, book_repository: BookRepository, member_repository: MemberRepository, loan_repository: LoanRepository) -> None:
        self._book_repository = book_repository
        self._member_repository = member_repository
        self._loan_repository = loan_repository

    def run_operations(self, storage_path: str) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"created_loans": [], "skipped": []}
        return summary

    def create_loan(self, book_id: str, member_id: str, storage_path: str) -> Dict[str, Any]:
        book: Optional[Dict[str, Any]] = self._book_repository.find(book_id, storage_path)
        if book is None:
            return {"success": False, "reason": "book_not_found"}
        if book.get("copies_available", 0) <= 0:
            return {"success": False, "reason": "no_available_copies"}
        member: Optional[Dict[str, Any]] = self._member_repository.find(member_id, storage_path)
        if member is None:
            return {"success": False, "reason": "member_not_found"}
        active_loans: List[Dict[str, Any]] = self._loan_repository.list_active_by_member(member_id, storage_path)
        active_count: int = len(active_loans) if active_loans is not None else 0
        if active_count >= member.get("loan_limit", 0):
            return {"success": False, "reason": "member_limit_reached"}
        loan_id = f"{book_id}-{member_id}-1"
        loan_dict: Dict[str, Any] = {
            "loan_id": loan_id,
            "book_id": book_id,
            "member_id": member_id,
            "loan_date": "1970-01-01",
            "due_date": "1970-01-01",
            "returned": False,
        }
        book["copies_available"] = book.get("copies_available", 0) - 1
        self._book_repository.update(book, storage_path)
        if "current_loans" in member:
            member["current_loans"] = member.get("current_loans", 0) + 1
        self._member_repository.update(member, storage_path)
        created = self._loan_repository.create(loan_dict, storage_path)
        return {"success": True, "loan": created if created is not None else loan_dict}
