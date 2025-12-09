import os
from typing import Any, Dict

from src.config import Config
from src.serializer import JsonSerializer
from src.atomic_writer import AtomicFileWriter
from src.repository import ExpenseRepository
from src.validator import ExpenseValidator
from src.service import ExpenseService, ValidationError, NotFoundError


def build_service() -> tuple[ExpenseService, Config]:
    """
    Wire up Config, JsonSerializer, AtomicFileWriter, ExpenseRepository,
    ExpenseValidator, and ExpenseService. Initialize the JSON store if needed.
    """
    config = Config()

    # Ensure data directory exists, e.g. "data/"
    store_dir = os.path.dirname(config.store_path) or "."
    os.makedirs(store_dir, exist_ok=True)

    serializer = JsonSerializer(
        field_order=config.serializer_field_order,
        indent=config.json_indent,
    )

    writer = AtomicFileWriter(
        fsync_after_write=True,
        temp_suffix=config.temp_suffix,
    )

    repository = ExpenseRepository(
        path=config.store_path,
        serializer=serializer,
        writer=writer,
    )

    # Create default store if file is missing/corrupted
    repository.initialize_store()

    validator = ExpenseValidator(
        allowed_categories=config.allowed_categories,
        description_max_length=config.description_max_length,
    )

    service = ExpenseService(repository=repository, validator=validator)
    return service, config


def prompt_expense_input(config: Config) -> Dict[str, Any]:
    """
    Ask user for expense fields and build a dict suitable for ExpenseService.add_expense.
    """
    print("\nEnter new expense:")
    date = input("  Date (YYYY-MM-DD): ").strip()
    amount = input("  Amount (e.g. 12.50): ").strip()

    print(f"  Category (one of: {', '.join(config.allowed_categories)} )")
    category = input("  Category: ").strip()

    description = input("  Description (optional, empty = none): ").strip()
    if description == "":
        description = None

    return {
        "date": date,
        "amount": amount,       # validator will convert to Decimal
        "category": category,
        "description": description,
    }


def main() -> None:
    service, config = build_service()

    print(f"ExpenseTracker ready. JSON store: {config.store_path}")
    while True:
        print("\n=== ExpenseTracker CLI ===")
        print("1) List expenses")
        print("2) Add expense")
        print("3) Update expense")
        print("4) Delete expense")
        print("5) Show settings")
        print("6) Update settings (currency)")
        print("0) Exit")

        choice = input("Select option: ").strip()

        if choice == "0":
            print("Exiting.")
            break

        elif choice == "1":
            # List expenses
            expenses = service.list_expenses()
            if not expenses:
                print("No expenses yet.")
            else:
                print("\nCurrent expenses:")
                for e in expenses:
                    print(
                        f"  id={e.get('id')} "
                        f"date={e.get('date')} "
                        f"amount={e.get('amount')} "
                        f"category={e.get('category')} "
                        f"description={e.get('description')}"
                    )

        elif choice == "2":
            # Add expense
            data = prompt_expense_input(config)
            try:
                created = service.add_expense(data)
                print("\nCreated expense:")
                print(created)
            except ValidationError as ve:
                print("\nValidation failed:")
                # your ValidationError has .errors mapping
                if hasattr(ve, "errors"):
                    for field, msg in ve.errors.items():
                        print(f"  {field}: {msg}")
                else:
                    print(str(ve))

        elif choice == "3":
            # Update expense
            try:
                expense_id = int(input("Enter expense id to update: ").strip())
            except ValueError:
                print("Invalid id.")
                continue

            print("Leave a field empty to keep current value.")
            patch: Dict[str, Any] = {}
            date = input("  New date (YYYY-MM-DD, blank = keep): ").strip()
            if date:
                patch["date"] = date
            amount = input("  New amount (blank = keep): ").strip()
            if amount:
                patch["amount"] = amount
            category = input("  New category (blank = keep): ").strip()
            if category:
                patch["category"] = category
            desc = input("  New description (blank = keep, '-' to clear): ").strip()
            if desc == "-":
                patch["description"] = None
            elif desc:
                patch["description"] = desc

            try:
                updated = service.update_expense(expense_id, patch)
                print("\nUpdated expense:")
                print(updated)
            except NotFoundError as nf:
                print(f"\nError: {nf}")
            except ValidationError as ve:
                print("\nValidation failed:")
                if hasattr(ve, "errors"):
                    for field, msg in ve.errors.items():
                        print(f"  {field}: {msg}")
                else:
                    print(str(ve))

        elif choice == "4":
            # Delete expense
            try:
                expense_id = int(input("Enter expense id to delete: ").strip())
            except ValueError:
                print("Invalid id.")
                continue

            try:
                service.delete_expense(expense_id)
                print(f"Deleted expense id={expense_id}.")
            except NotFoundError as nf:
                print(f"\nError: {nf}")

        elif choice == "5":
            # Show settings
            settings = service.get_settings()
            print("\nCurrent settings:")
            for k, v in settings.items():
                print(f"  {k}: {v}")

        elif choice == "6":
            # Update settings (only currency for now)
            new_curr = input("Enter new currency (3-letter code, e.g. PLN, EUR): ").strip()
            try:
                updated = service.update_settings({"currency": new_curr})
                print("\nUpdated settings:")
                print(updated)
            except ValidationError as ve:
                print("\nValidation failed:")
                if hasattr(ve, "errors"):
                    for field, msg in ve.errors.items():
                        print(f"  {field}: {msg}")
                else:
                    print(str(ve))

        else:
            print("Unknown option. Please choose 0–6.")


if __name__ == "__main__":
    main()
