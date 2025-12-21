from typing import Dict, Any

from domain.transaction_service import TransactionService
from domain.category_service import CategoryService
from app_logging import AppLogger


class CommandController:
    """Controller that translates a generic command dict into concrete domain service calls.

    Responsibilities (per manifest):
    - Validate incoming command against the documented command contract (conservative enforcement).
    - Dispatch to TransactionService or CategoryService according to command['entity'] and command['action'].
    - Log intent, validation failures, routing decisions, service errors, and successes via the injected AppLogger.
    """

    # Embedded conservative command contract (from manifest) used for validation.
    command_contract = {
        "type": "object",
        "required": ["entity", "action"],
        "properties": {
            "entity": {"type": "string", "enum": ["transaction", "category"]},
            "action": {"type": "string", "enum": ["create", "list", "get", "update", "delete"]},
            "params": {"type": "object"}
        },
        "additionalProperties": False,
    }

    def __init__(
        self,
        transaction_service: TransactionService,
        category_service: CategoryService,
        logger: AppLogger,
    ) -> None:
        # Assign dependencies per manifest
        self._transaction_service = transaction_service
        self._category_service = category_service
        self._logger = logger

    def handle(self, command: Dict[str, Any], data_dir: str) -> dict:
        """Validate and dispatch a command to the appropriate domain service.

        Returns a dict representing either the service result (if dict it's returned as-is; otherwise wrapped under 'result')
        or a normalized error shape with an 'error' key.
        """
        # Basic structural validation (conservative, implemented without external jsonschema dependency)
        if not isinstance(command, dict):
            self._logger.error("Command validation failed: command must be a dict", command)
            return {"error": "validation_error", "details": "command must be a dict"}

        entity = command.get("entity")
        action = command.get("action")
        params = command.get("params", {}) if command.get("params") is not None else {}

        if not isinstance(entity, str) or entity not in ("transaction", "category"):
            self._logger.error("Command validation failed: invalid or missing 'entity'", {"entity": entity})
            return {
                "error": "validation_error",
                "details": "'entity' must be one of ['transaction', 'category']",
            }

        if not isinstance(action, str) or action not in ("create", "list", "get", "update", "delete"):
            self._logger.error("Command validation failed: invalid or missing 'action'", {"action": action})
            return {
                "error": "validation_error",
                "details": "'action' must be one of ['create', 'list', 'get', 'update', 'delete']",
            }

        if not isinstance(params, dict):
            self._logger.error("Command validation failed: 'params' must be an object if provided", {"params": params})
            return {"error": "validation_error", "details": "'params' must be an object if provided"}

        self._logger.debug("Interpreting command", {"entity": entity, "action": action, "params": params})

        # Choose service based on entity
        try:
            if entity == "transaction":
                svc = self._transaction_service
                if action == "create":
                    record = params.get("record")
                    if not isinstance(record, dict) or "id" not in record:
                        self._logger.error("Create command missing required record or id", {"record": record})
                        return {
                            "error": "validation_error",
                            "details": "create requires params.record with an 'id' field",
                        }
                    result = svc.create(record, data_dir)

                elif action == "list":
                    query = params if isinstance(params, dict) else {}
                    result = svc.list(query, data_dir)

                elif action == "get":
                    record_id = params.get("id") or params.get("record_id")
                    if not isinstance(record_id, str):
                        self._logger.error("Get command missing record id", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "get requires params.id or params.record_id",
                        }
                    result = svc.get(record_id, data_dir)

                elif action == "update":
                    record_id = params.get("id") or params.get("record_id")
                    update_fields = params.get("update_fields")
                    if not isinstance(record_id, str) or not isinstance(update_fields, dict):
                        self._logger.error("Update command missing id or update_fields", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "update requires params.id (or params.record_id) and params.update_fields (dict)",
                        }
                    result = svc.update(record_id, update_fields, data_dir)

                elif action == "delete":
                    record_id = params.get("id") or params.get("record_id")
                    if not isinstance(record_id, str):
                        self._logger.error("Delete command missing record id", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "delete requires params.id or params.record_id",
                        }
                    result = svc.delete(record_id, data_dir)

                else:
                    # Defensive: should not reach due to earlier validation
                    self._logger.error("Unsupported transaction action", {"action": action})
                    return {"error": "unsupported_action"}

            else:  # entity == "category"
                svc = self._category_service
                if action == "create":
                    record = params.get("record")
                    if not isinstance(record, dict) or "id" not in record:
                        self._logger.error("Create category missing required record or id", {"record": record})
                        return {
                            "error": "validation_error",
                            "details": "create requires params.record with an 'id' field",
                        }
                    result = svc.create(record, data_dir)

                elif action == "list":
                    query = params if isinstance(params, dict) else {}
                    result = svc.list(query, data_dir)

                elif action == "get":
                    record_id = params.get("id") or params.get("record_id")
                    if not isinstance(record_id, str):
                        self._logger.error("Get category missing record id", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "get requires params.id or params.record_id",
                        }
                    result = svc.get(record_id, data_dir)

                elif action == "update":
                    record_id = params.get("id") or params.get("record_id")
                    update_fields = params.get("update_fields")
                    if not isinstance(record_id, str) or not isinstance(update_fields, dict):
                        self._logger.error("Update category missing id or update_fields", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "update requires params.id (or params.record_id) and params.update_fields (dict)",
                        }
                    result = svc.update(record_id, update_fields, data_dir)

                elif action == "delete":
                    record_id = params.get("id") or params.get("record_id")
                    if not isinstance(record_id, str):
                        self._logger.error("Delete category missing record id", {"params": params})
                        return {
                            "error": "validation_error",
                            "details": "delete requires params.id or params.record_id",
                        }
                    result = svc.delete(record_id, data_dir)

                else:
                    self._logger.error("Unsupported category action", {"action": action})
                    return {"error": "unsupported_action"}

        except Exception as exc:  # Log and normalize unexpected service errors
            # Avoid exposing internal exception traces in normal responses; include message for diagnostics
            self._logger.error("Service call failed during command handling", {"exception": str(exc)})
            return {"error": "internal_error", "details": str(exc)}

        # Log success and normalize return shape to a dict per manifest guidance
        self._logger.info("Command dispatched to service", {"entity": entity, "action": action})

        if isinstance(result, dict):
            return result
        return {"result": result}
