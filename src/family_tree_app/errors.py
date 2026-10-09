"""
Error Handling and Validation Convention

1. Unexpected / System Errors (e.g., SQLite locks, missing files, memory issues):
   - Do NOT catch these in the repository layer. Let standard exceptions (e.g. `sqlite3.Error`, `OSError`) propagate.
   - The UI layer will use a global exception handler (e.g. overriding `sys.excepthook` or a high-level try/except)
     that logs the stack trace and presents a generic "Unexpected Error" dialog to the user.

2. Validation / Business Logic Errors:
   - When user data violates rules (e.g. "End date is before start date", "Cannot be your own ancestor"),
     the repository or service layer should raise a `ValidationError`.
   - The message in `ValidationError` MUST be friendly and safe to show directly to the user.
   - Individual UI screens will catch `ValidationError` specifically and display the message in a
     standard warning dialog, leaving the screen open so the user can correct their input.
"""

class FamilyTreeError(Exception):
    """Base exception for all application-specific errors."""
    pass

class ValidationError(FamilyTreeError):
    """Raised when data validation or business logic fails. Message is user-facing."""
    pass
