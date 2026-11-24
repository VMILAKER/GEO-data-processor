import os
from pathlib import Path

from src.services import READERS, METADATA, ALIASES, dep, bounded

import json

reader_options = {}

mapping = {
    "depth": "depth [m]",
    "temperature": "temperature [ITS-90, deg C]",
    "salinity": "salinity [PSU]",
}

constants = {
    "Type": "B", 
    "Monitor": "1",
}

primary = "depth [m]"

measurements = {
    "temperature [ITS-90, deg C]": "ITS-90, deg C",
    "salinity [PSU]": "PSU",
}


def write_odv_style(frame,mapping=None, constants=None, primary='Depth [m]',
              measurements=None, max_rows=1_000_000):
    pd = dep('pandas')
    result = bounded(frame.copy(), max_rows)
    renames = {c: ALIASES.get(str(c).strip().lower(), c)
                for c in result.columns}
    renames.update(mapping or {})
    result = result.rename(columns=renames)
    if result.columns.duplicated().any():
        raise ValueError('Duplicate column names after mapping')
    for key, value in (constants or {}).items():
        result[key] = value
    required = METADATA + [primary]
    missing = [c for c in required if c not in result]
    if missing:
        raise ValueError(
            f'Missing columns {missing}; supply mapping/constants, not invented metadata')
    if not measurements:
        raise ValueError('Explicit measurements with units required')
    for col in measurements:
        if col not in result or col in required:
            raise ValueError(f'Invalid measurement column {col}')
        if '[' not in col or ']' not in col:
            raise ValueError(f'Measurement needs units in header: {col}')
        result[col] = pd.to_numeric(result[col], errors='raise')
    if result.empty:
        raise ValueError('No observations')
    if result[required].isna().any().any():
        raise ValueError(
            'Mandatory metadata or primary coordinate contain missing values')
    for col in ('Cruise', 'Station', 'Type'):
        result[col] = result[col].astype(str)
        if result[col].str.strip().eq('').any():
            raise ValueError(f'Empty {col}')
    if not result['Type'].isin(['C', 'B']).all():
        raise ValueError('ODV Type must be C (CTD) or B (bottle)')
    for col, limit in [('Longitude [degrees_east]', 180), ('Latitude [degrees_north]', 90)]:
        result[col] = pd.to_numeric(result[col], errors='raise')
        if not result[col].between(-limit, limit).all():
            raise ValueError(
                f'Out-of-range {col}; normalize/transform coordinates first')
    result[primary] = pd.to_numeric(result[primary], errors='raise')
    times = pd.to_datetime(
        result['yyyy-mm-ddThh:mm:ss'], utc=True, errors='raise')
    result['yyyy-mm-ddThh:mm:ss'] = times.dt.strftime('%Y-%m-%dT%H:%M:%S')
    for _, group in result.groupby(['Cruise', 'Station'], dropna=False):
        for col in METADATA[2:]:
            if group[col].nunique(dropna=False) != 1:
                raise ValueError(
                    'Station has varying metadata; define distinct stations/profiles')
    selected = result[required + list(measurements)]
    if selected.astype(str).apply(lambda col: col.str.contains(r'[\t\r\n]')).any().any():
        raise ValueError('Embedded tabs/newlines not permitted')
    return result.to_json()


def file_processing(file_path: str, *, reader_options=None, mapping=None,
         constants=None, primary='Depth [m]', measurements=None):
    """Read supported source. If output_path is provided, validate/export ODV TXT.
    Without output_path return DataFrame (no implicit output.txt overwrite).
    """
    try:
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(source)
        reader = READERS.get(source.suffix.lower())
        if reader is None:
            raise ValueError(f'Unknown extension {source.suffix}')
        frame = reader(source, **(reader_options or {}))
        return write_odv_style(frame, mapping, constants, primary, measurements)
    except Exception as e:
        return str(e)
    


if __name__ == '__main__':
    list_analytics_data = []
    for n, i in enumerate(os.listdir('test_geodata')):
        if not i.endswith(('.zarr', '.py')):
            data = file_processing(
                os.path.join('test_geodata', i),
                reader_options=reader_options,
                mapping=mapping,
                constants=constants,
                primary=primary,
                measurements=measurements
            ) 
            # print(data)
            list_analytics_data.append({f'{i}': data})
    with open('analytics_for_test_data.json', 'w', encoding='utf-8') as f:
        json.dump(list_analytics_data, f,ensure_ascii=False, indent=2)