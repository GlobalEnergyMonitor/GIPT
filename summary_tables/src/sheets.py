"""pygsheets helpers for writing the summary tables.

Authentication uses the service-account JSON on the Shared Drive
(:data:`src.config.CREDS_FILE`); that account must have edit access to each
target sheet. ``pygsheets`` is imported lazily inside :func:`client` so the
pure build/inspect path works without it installed (e.g. for local testing).
"""

from . import config


def client(creds_file=None):
    """Authorise pygsheets with the service account."""
    import pygsheets
    return pygsheets.authorize(service_file=creds_file or config.CREDS_FILE)


def write_frame(spreadsheet, tab, df, anchor, extend=False):
    """Write ``df`` (values only) into worksheet ``tab`` starting at ``anchor``.

    Matches the original notebook's call — no header, no index, no auto-resize —
    so the values drop straight onto the sheet's existing template.
    """
    worksheet = spreadsheet.worksheet("title", tab)
    worksheet.set_dataframe(df, anchor, copy_index=False, copy_head=False,
                            extend=extend, fit=False)
    return worksheet
