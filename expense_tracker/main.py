import sys
import argparse
import logging
from typing import Dict, Any

# Ensure we can import from src
sys.path.append(".")

from src.controller import AppController
from src.service import ValidationError, NotFoundError

def setup_logging():
    """Configures basic logging to console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

def print_expense(expense: Dict[str, Any]):
    """Helper to print a single expense row."""
    # Handle optional description safely
    desc = expense.get('description') or ""
    print(f"{expense['id']:<4} | {expense['date']:<12} | {float(expense['amount']):<10.2f} | {expense['category']:<12} | {desc}")

def run_cli():
    # 1. Configure Argument Parser
    parser = argparse.ArgumentParser(description="Expense Tracker CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: list
    subparsers.add_parser("list", help="List all expenses")

    # Command: add
    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("amount", type=float, help="Expense amount")
    add_parser.add_argument("category", type=str, help="Category (e.g., food, transport)")
    add_parser.add_argument("date", type=str, help="Date (YYYY-MM-DD)")
    add_parser.add_argument("--desc", "-d", type=str, default=None, help="Optional description")

    # Command: delete
    del_parser = subparsers.add_parser("delete", help="Delete an expense by ID")
    del_parser.add_argument("id", type=int, help="ID of the expense to delete")

    # Command: settings
    subparsers.add_parser("settings", help="Show current settings")

    args = parser.parse_args()

    # If no arguments provided, print help
    if not args.command:
        parser.print_help()
        return

    # 2. Instantiate and Start Controller
    # The controller handles dependency injection and startup orchestration[cite: 101, 105].
    controller = AppController() 

    try:
        # Initialize store, validator, and repository [cite: 105]
        controller.start()
        
        # Get the business service [cite: 125]
        service = controller.get_service()

        # 3. Execute Commands
        if args.command == "list":
            expenses = service.list_expenses()
            print("\nID   | Date         | Amount     | Category     | Description")
            print("-" * 70)
            if not expenses:
                print("(No expenses found)")
            else:
                for exp in expenses:
                    print_expense(exp)
            print("-" * 70 + "\n")

        elif args.command == "add":
            payload = {
                "amount": args.amount,
                "category": args.category,
                "date": args.date,
                "description": args.desc
            }
            try:
                # Service delegates validation to ExpenseValidator [cite: 224]
                new_expense = service.add_expense(payload)
                print(f"\n[SUCCESS] Added expense #{new_expense['id']}")
            except ValidationError as ve:
                print(f"\n[ERROR] Validation failed: {ve}")
            except Exception as e:
                print(f"\n[ERROR] Could not add expense: {e}")

        elif args.command == "delete":
            try:
                service.delete_expense(args.id)
                print(f"\n[SUCCESS] Expense #{args.id} deleted.")
            except NotFoundError:
                print(f"\n[ERROR] Expense #{args.id} not found.")

        elif args.command == "settings":
            settings = service.get_settings()
            print(f"\nCurrent Settings: {settings}\n")

    except Exception as e:
        # Catch generic startup or runtime errors
        print(f"CRITICAL ERROR: {e}")
        logging.exception("An unexpected error occurred")
    
    finally:
        # 4. Clean Shutdown
        # Ensure resources/handles are closed properly [cite: 126]
        controller.shutdown()

if __name__ == "__main__":
    setup_logging()
    run_cli()