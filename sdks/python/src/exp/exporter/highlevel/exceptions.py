"""Custom exceptions for Exporter."""


class ExporterError(Exception):
    """Base error for Exporter."""


class ValidationError(ExporterError):
    """Error in validating parameters or return values."""


class ResourceError(ExporterError):
    """Error in resource operations."""


class FunctionError(ExporterError):
    """Error in function operations."""


class InvalidSignature(Exception):
    """Invalid signature for use with Exporter."""
