from pathlib import Path

import numpy as np

p=Path(__file__).resolve().parent
import h5py

for ext in ("h5","hdf5"):
    with h5py.File(p/f"grid.{ext}","w") as f:
        f.attrs["description"]="Synthetic surface data"
        for name,data,unit in [("latitude",[59.5,59.0],"degrees_north"),("longitude",[18.,18.5,19.],"degrees_east"),("temperature",[[8.1,8.2,8.3],[7.8,7.9,8.0]],"degree_Celsius")]:
            f.create_dataset(name,data=data).attrs["units"]=unit
import xarray as xr

with xr.open_dataset(p/"grid_classic.nc",engine="scipy") as ds:
    ds.to_netcdf(p/"grid_netcdf4.nc",engine="netcdf4",format="NETCDF4")
from cdflib import cdfwrite

f=cdfwrite.CDF(p/"profiles_nasa.cdf",delete=True)
for name,data in [("longitude",[18.,18.5]),("latitude",[59.,59.5]),("temperature",[8.1,8.2])]:
    f.write_var({"Variable":name,"Data_Type":cdfwrite.CDF.CDF_DOUBLE,"Num_Elements":1,"Rec_Vary":True,"Dim_Sizes":[]},var_data=np.array(data))
f.close()
from eccodes import (codes_grib_new_from_samples, codes_release, codes_set,
                     codes_set_values, codes_write)

h=codes_grib_new_from_samples("regular_ll_sfc_grib2")
for k,v in {"Ni":3,"Nj":2,"latitudeOfFirstGridPointInDegrees":59.5,"longitudeOfFirstGridPointInDegrees":18.,"latitudeOfLastGridPointInDegrees":59.,"longitudeOfLastGridPointInDegrees":19.,"iDirectionIncrementInDegrees":0.5,"jDirectionIncrementInDegrees":0.5,"shortName":"2t","dataDate":20260101,"dataTime":1200}.items():
    codes_set(h,k,v)
codes_set_values(h,np.array([8.1,8.2,8.3,7.8,7.9,8.])+273.15)
for ext in ("grib2","grb2","grib","grb"):
    with open(p/f"grid.{ext}","wb") as out:codes_write(h,out)
codes_release(h)
print("Created HDF5, NetCDF-4, NASA CDF and GRIB2 fixtures")
