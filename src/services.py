"""Readers for geographic data and validated tab-separated ODV export.
Optional dependencies are imported only by the relevant reader.
No invented coordinates, timestamps, station IDs or measurements are added.
"""
import importlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# import config as Config



ALIASES = {
    'cruise': 'Cruise', 'station': 'Station', 'type': 'Type',
    'time': 'yyyy-mm-ddThh:mm:ss', 'date': 'yyyy-mm-ddThh:mm:ss',
    'longitude': 'Longitude [degrees_east]', 'lon': 'Longitude [degrees_east]',
    'latitude': 'Latitude [degrees_north]', 'lat': 'Latitude [degrees_north]',
    'depth': 'Depth [m]', 'pressure': 'Pressure [dbar]',
}


METADATA = ['Cruise', 'Station', 'Type', 'yyyy-mm-ddThh:mm:ss',
            'Longitude [degrees_east]', 'Latitude [degrees_north]']

MAX_ROWS = 1_000_000

def dep(name):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise ImportError(
            f"Missing dependency {name}; install requirements.txt") from exc


def bounded(frame, max_rows=MAX_ROWS):
    if len(frame) > max_rows:
        raise ValueError(
            f"{len(frame)} rows exceed max_rows={max_rows}; subset source")
    return frame


def read_table(path, sep=None, **kwargs):
    pd = dep('pandas')
    if sep is None:
        sep = '\t' if Path(path).suffix.lower() == '.tsv' else None
    return pd.read_csv(path, sep=sep, engine='python', comment='/', **kwargs)


def read_excel(path, sheet_name=0, **kwargs):
    return dep('pandas').read_excel(path, sheet_name=sheet_name, **kwargs)


def read_json(path, record_path=None):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if isinstance(data, dict) and data.get('type') in ('FeatureCollection', 'Feature'):
        return read_vector(path)
    if record_path:
        for key in record_path.split('.'):
            data = data[key]
    if not isinstance(data, list):
        raise ValueError('JSON requires a list of records or record_path')
    return dep('pandas').json_normalize(data)


def read_parquet(path):
    pd = dep('pandas')
    frame = pd.read_parquet(path)
    if frame.attrs.get('geo') or 'geometry' in frame:
        try:
            return vector_frame(dep('geopandas').read_parquet(path))
        except Exception as exc:
            raise ValueError(
                'Geometry needs valid GeoParquet metadata') from exc
    return frame


def vector_frame(gdf, geometry_mode='points'):
    if gdf.crs is None:
        raise ValueError('CRS is missing; assign a verified source CRS first')
    gdf = gdf.to_crs(4326).copy()
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    if not gdf.geom_type.eq('Point').all():
        if geometry_mode != 'vertices':
            raise ValueError(
                'Non-point geometry: request geometry_mode="vertices" explicitly')
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
        records = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom.geom_type == 'Point':
                coords = [geom.coords[0]]
            elif geom.geom_type in ('LineString', 'LinearRing'):
                coords = list(geom.coords)
            elif geom.geom_type == 'Polygon':
                raise ValueError(
                    'Polygon conversion requires an application-specific sampling rule')
            else:
                raise ValueError(f'Unsupported geometry {geom.geom_type}')
            for coord in coords:
                record = row.drop(labels=gdf.geometry.name).to_dict()
                record.update(longitude=coord[0], latitude=coord[1])
                records.append(record)
        return dep('pandas').DataFrame(records)
    result = gdf.drop(columns=gdf.geometry.name)
    result['longitude'] = gdf.geometry.x
    result['latitude'] = gdf.geometry.y
    return dep('pandas').DataFrame(result)


def read_vector(path, layer=None, geometry_mode='points', source_crs=None):
    gpd = dep('geopandas')
    options = {'engine': 'pyogrio'}
    if layer is not None:
        options['layer'] = layer
    gdf = gpd.read_file(path, **options)
    if gdf.crs is None and source_crs:
        gdf = gdf.set_crs(source_crs)
    return vector_frame(gdf, geometry_mode)


def read_kml(path, member=None):
    if Path(path).suffix.lower() == '.kmz':
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith('.kml')]
            if member is None and len(names) != 1:
                raise ValueError(
                    'KMZ contains multiple/no KML files; specify member')
            xml = archive.read(member or names[0])
    else:
        xml = Path(path).read_bytes()
    root = ET.fromstring(xml)
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    records = []
    for pm in root.findall('.//k:Placemark', ns):
        if pm.find('.//k:LineString', ns) is not None or pm.find('.//k:Polygon', ns) is not None:
            raise ValueError(
                'KML line/polygon needs an explicit sampling rule')
        base = {'name': pm.findtext('k:name', default='', namespaces=ns)}
        when = pm.findtext('.//k:TimeStamp/k:when', namespaces=ns)
        if when:
            base['time'] = when
        for item in pm.findall('.//k:Data', ns):
            base[item.attrib['name']] = item.findtext('k:value', namespaces=ns)
        for item in pm.findall('.//k:SimpleData', ns):
            base[item.attrib['name']] = item.text
        for point in pm.findall('.//k:Point', ns):
            text = point.findtext('k:coordinates', namespaces=ns)
            if not text:
                continue
            vals = text.strip().split(',')
            record = dict(base, longitude=float(
                vals[0]), latitude=float(vals[1]))
            if len(vals) > 2:
                record['altitude'] = float(vals[2])  # not automatically depth
            records.append(record)
    if not records:
        raise ValueError('No KML Points found')
    return dep('pandas').DataFrame(records)


def dataset_frame(ds, variables=None, selectors=None, max_rows=MAX_ROWS):
    import math
    if selectors:
        ds = ds.sel(selectors)
    if variables:
        ds = ds[list(variables)]
    size = math.prod(ds.sizes.values())
    if size > max_rows:
        raise ValueError(
            f'Cartesian expansion may produce {size} rows; use selectors/variables')
    return bounded(ds.to_dataframe().reset_index(), max_rows)


def read_netcdf(path, variables=None, selectors=None, group=None, max_rows=MAX_ROWS):
    xr = dep('xarray')
    with xr.open_dataset(path, group=group) as ds:
        return dataset_frame(ds, variables, selectors, max_rows)


def read_zarr(path, variables=None, selectors=None, max_rows=MAX_ROWS):
    xr = dep('xarray')
    with xr.open_zarr(path, consolidated=None) as ds:
        return dataset_frame(ds, variables, selectors, max_rows)


def read_grib(path, variables=None, selectors=None, filter_by_keys=None, max_rows=MAX_ROWS):
    xr = dep('xarray')
    dep('cfgrib')
    options = {'indexpath': ''}
    if filter_by_keys:
        options['filter_by_keys'] = filter_by_keys
    with xr.open_dataset(path, engine='cfgrib', backend_kwargs=options) as ds:
        return dataset_frame(ds, variables, selectors, max_rows)


def read_hdf5(path, datasets=None, max_rows=MAX_ROWS):
    """datasets maps output column -> dataset path; no guessed array alignment."""
    if not datasets:
        raise ValueError(
            'HDF5 requires datasets={column: dataset_path}; arrays must have equal shapes')
    h5py = dep('h5py')
    np = dep('numpy')
    pd = dep('pandas')
    with h5py.File(path, 'r') as f:
        shapes = [f[value].shape for value in datasets.values()]
        if len(set(shapes)) != 1:
            raise ValueError(
                'HDF5 shapes differ; use product-specific adapter to align axes')
        if np.prod(shapes[0]) > max_rows:
            raise ValueError('HDF5 dataset exceeds max_rows')
        data = {key: f[value][()].reshape(-1)
                for key, value in datasets.items()}
    return pd.DataFrame(data)


def read_cdf(path, variables=None, **kwargs):
    with open(path, 'rb') as f:
        magic = f.read(8)
    if magic.startswith(b'CDF') or magic == b'\x89HDF\r\n\x1a\n':
        return read_netcdf(path, variables=variables, **kwargs)
    cdflib = dep('cdflib')
    np = dep('numpy')
    pd = dep('pandas')
    cdf = cdflib.CDF(str(path))
    info = cdf.cdf_info()
    names = variables or list(info.rVariables) + list(info.zVariables)
    arrays = {}
    for name in names:
        data = np.asarray(cdf.varget(name))
        if data.ndim != 1:
            raise ValueError(
                f'NASA CDF {name}: choose scalar record variables or supply custom adapter')
        arrays[name] = data
    if len({len(a) for a in arrays.values()}) > 1:
        raise ValueError('NASA CDF variables have different record counts')
    return bounded(pd.DataFrame(arrays), kwargs.get('max_rows', MAX_ROWS))


def read_geotiff(path, bands=None, max_rows=MAX_ROWS):
    rio = dep('rasterio')
    np = dep('numpy')
    pd = dep('pandas')
    Transformer = dep('pyproj').Transformer
    with rio.open(path) as src:
        if src.crs is None:
            raise ValueError('GeoTIFF requires a verified CRS')
        if src.width * src.height > max_rows:
            raise ValueError(
                'Raster exceeds max_rows; crop it before conversion')
        rr, cc = np.indices((src.height, src.width))
        xs, ys = rio.transform.xy(src.transform, rr.ravel(), cc.ravel())
        lon, lat = Transformer.from_crs(
            src.crs, 4326, always_xy=True).transform(xs, ys)
        data = {'longitude': lon, 'latitude': lat}
        for band in bands or range(1, src.count + 1):
            data[f'band_{band}'] = src.read(band, masked=True).astype(
                float).filled(np.nan).ravel()
    return pd.DataFrame(data).dropna(subset=[c for c in data if c.startswith('band_')], how='all')


def read_cnv(path, encoding='utf-8'):
    """Processed ASCII Sea-Bird CNV only, not binary/raw instrument streams."""
    import re
    text = Path(path).read_text(encoding=encoding)
    if '*END*' not in text:
        raise ValueError('CNV requires *END* marker')
    header, data = text.split('*END*', 1)
    names = re.findall(r'^#\s*name\s+\d+\s*=\s*(.*)$', header, re.M)
    if not names:
        raise ValueError('CNV column definitions missing')
    return dep('pandas').read_csv(io.StringIO(data), sep=r'\s+', names=names, comment='*')


def read_postgis(query, connection_url, geom_col='geom', geometry_mode='points'):
    """Requires existing PostgreSQL/PostGIS server. Use trusted SQL queries only."""
    engine = dep('sqlalchemy').create_engine(connection_url)
    try:
        return vector_frame(dep('geopandas').read_postgis(query, engine, geom_col=geom_col), geometry_mode)
    finally:
        engine.dispose()


def unsupported(path):
    raise NotImplementedError(
        f'{Path(path).suffix}: no verified generic parser. Provide a specification or export from source software; renaming the extension is not conversion.')


def write_odv(frame, output_path, mapping=None, constants=None, primary='Depth [m]',
              measurements=None, max_rows=MAX_ROWS):
    """mapping: source column -> ODV name; constants are caller-supplied metadata.
    Measurements must be explicit, e.g. ['Temperature [degC]','Salinity [psu]'].
    Units are labels only: physical unit conversion must be done by caller.
    """
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
    out = Path(output_path)
    if out.suffix.lower() != '.txt':
        raise ValueError('Output extension must be .txt')
    out.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(out, sep='\t', index=False, encoding='utf-8', na_rep='')
    return out


READERS = {
    '.csv': read_table, '.tsv': read_table, '.txt': read_table,
    '.xlsx': read_excel, '.xls': read_excel, '.json': read_json,
    '.geojson': read_vector, '.shp': read_vector, '.gpkg': read_vector, '.gml': read_vector,
    '.kml': read_kml, '.kmz': read_kml, '.nc': read_netcdf, '.nc4': read_netcdf,
    '.netcdf': read_netcdf, '.cdf': read_cdf, '.h5': read_hdf5, '.hdf5': read_hdf5,
    '.zarr': read_zarr, '.tif': read_geotiff, '.tiff': read_geotiff,
    '.parquet': read_parquet, '.grib': read_grib, '.grb': read_grib,
    '.grib2': read_grib, '.grb2': read_grib, '.cnv': read_cnv,
    '.var': unsupported, '.nce': unsupported, '.jos': unsupported, '.odv': unsupported,
}