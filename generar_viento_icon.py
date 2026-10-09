import os
import bz2
import urllib.request
import json
import numpy as np
import xarray as xr

URL_BASE = "https://opendata.dwd.de/weather/ncm/ICON-EU/grib"

def obtener_url_valida(tipo_var):
    corridas = ["00", "06", "12", "18"]
    for corrida in corridas:
        url = f"{URL_BASE}/{corrida}/{tipo_var}/icon-eu_europe_regular-lat-lon_single-level_latest_000_10_{tipo_var}.grib2.bz2"
        try:
            print(f"Probando conexion con: {url}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    print(f"  -> ¡Encontrado archivo valido en corrida {corrida}!")
                    return url
        except Exception as e:
            print(f"  -> No disponible corrida {corrida}: {e}")
    raise RuntimeError(f"No se pudo encontrar ninguna URL funcional para {tipo_var}")

def descargar_y_descomprimir(url, file_bz2, file_grib):
    print(f"Descargando {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(file_bz2, 'wb') as out_file:
        out_file.write(response.read())
    
    print(f"Descomprimiendo {file_bz2} -> {file_grib}...")
    with bz2.BZ2File(file_bz2, 'rb') as source, open(file_grib, 'wb') as target:
        target.write(source.read())
    
    if os.path.exists(file_bz2):
        os.remove(file_bz2)

FILE_U_GRIB = "u10.grib2"
FILE_V_GRIB = "v10.grib2"
JSON_OUTPUT = "viento-espana.json"

try:
    url_u = obtener_url_valida("u10")
    url_v = obtener_url_valida("v10")

    descargar_y_descomprimir(url_u, "u10.grib2.bz2", FILE_U_GRIB)
    descargar_y_descomprimir(url_v, "v10.grib2.bz2", FILE_V_GRIB)

    print("Procesando datasets con Xarray / cfgrib...")
    ds_u = xr.open_dataset(FILE_U_GRIB, engine='cfgrib')
    ds_v = xr.open_dataset(FILE_V_GRIB, engine='cfgrib')

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
                "parameterNumber": 2,
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
                "parameterNumber": 3,
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

    print(f"Escribiendo resultado en {JSON_OUTPUT}...")
    with open(JSON_OUTPUT, 'w') as f:
        json.dump(wind_data, f)

    for f in [FILE_U_GRIB, FILE_V_GRIB]:
        if os.path.exists(f):
            os.remove(f)

    print("✅ ¡Exito! Archivo viento-espana.json generado.")

except Exception as e:
    print(f"❌ Error durante la ejecucion: {e}")
    raise e
