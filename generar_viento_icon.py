import os
import bz2
import urllib.request
import re
import json
import numpy as np
import xarray as xr

URL_BASE = "https://opendata.dwd.de/weather/ncm/ICON-EU/grib"

def obtener_url_dinamica(var_folder, var_code):
    """
    Escanea el índice HTML de la carpeta del DWD para encontrar el archivo .grib2.bz2 más reciente.
    """
    corridas = ["00", "06", "12", "18"]
    # Probamos las corridas desde la más reciente hasta la más antigua
    for corrida in reversed(corridas):
        folder_url = f"{URL_BASE}/{corrida}/{var_folder}/"
        try:
            print(f"Buscando archivos en: {folder_url}")
            req = urllib.request.Request(folder_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                html = resp.read().decode('utf-8')
                
                # Buscar todos los enlaces a archivos .grib2.bz2 con el código de variable
                patron = r'href=["\']([^"\']+\.' + re.escape(var_code) + r'\.grib2\.bz2)["\']'
                archivos = re.findall(patron, html, re.IGNORECASE)
                
                if archivos:
                    # Seleccionamos el último archivo disponible de la lista
                    archivo_encontrado = archivos[-1]
                    url_completa = folder_url + archivo_encontrado
                    print(f"  -> ¡Archivo encontrado en corrida {corrida}!: {archivo_encontrado}")
                    return url_completa
        except Exception as e:
            print(f"  -> Error escaneando corrida {corrida}: {e}")
            
    raise RuntimeError(f"No se pudo encontrar ningún archivo válido para la variable {var_code}")

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
    # Escanear y obtener las URLs dinámicas reales
    url_u = obtener_url_dinamica("u10", "u10")
    url_v = obtener_url_dinamica("v10", "v10")

    descargar_y_descomprimir(url_u, "u10.grib2.bz2", FILE_U_GRIB)
    descargar_y_descomprimir(url_v, "v10.grib2.bz2", FILE_V_GRIB)

    print("Procesando datasets con Xarray / cfgrib...")
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
                "parameterNumber": 2,  # Componente U (Este-Oeste)
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
                "parameterNumber": 3,  # Componente V (Norte-Sur)
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

    print("✅ ¡Éxito! Archivo viento-espana.json generado correctamente.")

except Exception as e:
    print(f"❌ Error durante la ejecución: {e}")
    raise e
except Exception as e:
    print(f"❌ Error durante la ejecucion: {e}")
    raise e
