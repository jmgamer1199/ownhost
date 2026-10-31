class UserError(Exception):
    """Error shown to the user as is (400)."""


class CodeRejected(UserError):
    """The other computer did not accept the backup code (replicas)."""
