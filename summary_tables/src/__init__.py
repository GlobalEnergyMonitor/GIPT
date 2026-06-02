"""GIPT summary-table updater.

Load the source data once with :func:`src.data.load_gipt`, then run each
workbook updater in :mod:`src.workbooks` independently. Configuration (file
paths, sheet keys, category lists) lives in :mod:`src.config`.
"""
