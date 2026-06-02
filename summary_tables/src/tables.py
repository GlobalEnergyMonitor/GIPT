"""Small dataframe-shaping helpers shared by the workbook builders."""


def ensure_dimensions(df, index_levels, column_levels, index_name=None, fill_value=0.0):
    """Force ``df`` onto a fixed set of rows and columns.

    Missing columns and index entries are added with ``fill_value``; everything
    is then reordered to exactly ``index_levels`` x ``column_levels``. This pins
    a region table to the canonical region/technology layout regardless of what
    the data happened to contain (extra areas are dropped, missing ones become 0).
    """
    df = df.copy()
    for col in set(column_levels) - set(df.columns):
        df[col] = fill_value
    for idx in set(index_levels) - set(df.index):
        df.loc[idx] = fill_value
    df = df.loc[index_levels, column_levels].fillna(fill_value)
    if index_name:
        df.index.name = index_name
    return df
