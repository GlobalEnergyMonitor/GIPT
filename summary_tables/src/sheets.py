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


def open_sheet(key, gc=None):
    """Open a spreadsheet by key, authorising first if no client is given."""
    gc = gc or client()
    return gc.open_by_key(key)


def url(key):
    """The edit URL for a spreadsheet key (handy for run summaries / banners)."""
    return f"https://docs.google.com/spreadsheets/d/{key}/edit"


def write_frame(spreadsheet, tab, df, anchor,
                copy_head=False, copy_index=False, extend=False, fit=False):
    """Write ``df`` into worksheet ``tab`` starting at ``anchor``.

    All of pygsheets' ``set_dataframe`` flags are exposed so a single tab can be
    written with full control, exactly like the original notebook's per-tab
    calls. Defaults match the common case: values only (no header, no index),
    onto the sheet's existing template.
    """
    worksheet = spreadsheet.worksheet("title", tab)
    worksheet.set_dataframe(df, anchor, copy_head=copy_head, copy_index=copy_index,
                            extend=extend, fit=fit)
    return worksheet
