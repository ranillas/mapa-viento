import os
import bz2
import urllib.request
import xarray as xr
import json
import numpy as np

# URLs base con fallbacks para garantizar disponibilidad de archivos en el DWD
URLS_U = [
    "https://opendata.dwd.de/weather/ncm/ICON-EU/grib/00/u10/icon-eu_europe_regular-lat-lon_single-level_latest_000_10_u10.grib2.bz2",
    "https://opendata.dwd.de/weather/ncm/ICON-EU/grib/06/u10/icon-eu_europe_regular-lat-lon_single-level_latest_000_10_u10.grib2.bz2"
]

URLS_V = [
    "https://opendata.dwd.de/weather/ncm/ICON-EU/grib/00/v10/icon-eu_europe_regular-lat-lon_single-level_latest_000_10_v10.grib2.bz2",
    "https://opendata.dwd.de/weather/ncm/ICON-EU/grib/06/v10/icon-eu_europe_regular-lat-lon_single-level_latest_000_10_v10.grib2.bz2"
]

FILE_U_BZ2 = "u10.grib2.bz2"
FILE_V_BZ2 = "v10.grib2.bz2"
FILE_U_GRIB = "u10.grib2"
FILE_V_GRIB = "v10.grib2"
JSON_OUTPUT = "viento-espana.json"

def descargar_con_fallback(urls, file_bz2, file_grib):
    exito = False
    for url in urls:
        try:
            print(f"Probando descarga desde: {url}")
            # Añadimos un User-Agent para evitar bloqueos HTTP 403/400
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(file_bz2, 'wb') as out_file:
                out_file.write(response.read())
            
            print(f"Descomprimiendo {file_bz2}...")
            with bz2.BZ2File(file_bz2, 'rb') as source, open(file_grib, 'wb') as target:
                target.write(source.read())
            
            if os.path.exists(file_bz2):
                os.remove(file_bz2)
            exito = True
            break
        except Exception as err:
            print(f"⚠️ Falló descarga de {url}: {err}")
            if os.path.exists(file_bz2):
                os.remove(file_bz2)
    
    if not exito:
        raise RuntimeError("No se pudo descargar el archivo de viento desde ninguna de las URLs de origen.")

try:
    descargar_con_fallback(URLS_U, FILE_U_BZ2, FILE_U_GRIB)
    descargar_con_fallback(URLS_V, FILE_V_BZ2, FILE_V_GRIB)

    print("Procesando mallas de viento con Xarray...")
    ds_u = xr.open_dataset(FILE_U_GRIB, engine='cfgrib')
    ds_v = xr.open_dataset(FILE_V_GRIB, engine='cfgrib')

    # Recorte para España y Península Ibérica
    lat_bounds = (35.0, 44.5)
    lon_bounds = (-10.0, 4.5)

    u_sub = ds_u['u10'].sel(latitude=slice(lat_bounds[1], lat_bounds[0]), longitude=slice(lon_bounds[0], lon_bounds[1]))
    v_sub = ds_v['v10'].sel(latitude=slice(lat_bounds[1], lat_bounds[0]), longitude=slice(lon_bounds[0], lon_bounds[1]))

    lats = u_sub.latitude.values
    lons = u_sub.longitude.values
    u_vals = u_sub.values
    v_vals = v_sub.values

    ny, nx = u_vals.shape

    wind_data = [
        {
            "header": {
                "parameterCategory": 2,
                "parameterNumber": 2,  # Componente U
                "nx": int(nx),
                "ny": int(ny),
                "basicAngle": 0,
                "subCenter": 0,
                "lo1": float(lons.min()),
                "la1": float(lats.max()),
                "lo2": float(lons.max()),
                "la2": float(lats.min()),
                "dx": float(abs(lons[1] - lons[0])),
                "dy": float(abs(lats[1] - lats[0]))
            },
            "data": np.nan_to_num(u_vals).flatten().tolist()
        },
        {
            "header": {
                "parameterCategory": 2,
                "parameterNumber": 3,  # Componente V
                "nx": int(nx),
                "ny": int(ny),
                "basicAngle": 0,
                "subCenter": 0,
                "lo1": float(lons.min()),
                "la1": float(lats.max()),
                "lo2": float(lons.max()),
                "la2": float(lats.min()),
                "dx": float(abs(lons[1] - lons[0])),
                "dy": float(abs(lats[1] - lats[0]))
            },
            "data": np.nan_to_num(v_vals).flatten().tolist()
        }
    ]

    print(f"Guardando {JSON_OUTPUT}...")
    with open(JSON_OUTPUT, 'w') as f:
        json.dump(wind_data, f)

    for f in [FILE_U_GRIB, FILE_V_GRIB]:
        if os.path.exists(f):
            os.remove(f)

    print("✅ Archivo ICON-EU 'viento-espana.json' generado correctamente.")

except Exception as e:
    print(f"❌ Error al procesar ICON-EU: {e}")
    raise e
