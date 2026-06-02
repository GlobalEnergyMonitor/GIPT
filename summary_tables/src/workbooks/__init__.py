"""One module per target Google Sheet.

Each workbook module exposes ``build`` (pure: compute the frames to write),
``push`` (write them via pygsheets), and ``run`` (orchestrate, default
``write=False`` so you can inspect before committing). Added from Step 2 on.
"""
