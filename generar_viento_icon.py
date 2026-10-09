import os
import bz2
import json
import re
import requests
import numpy as np
import xarray as xr

# Ruta oficial confirmada de predicción numérica de ICON-EU
URL_BASE_NWP = "https://opendata.dwd.de/weather/nwp/icon-eu/grib"

def crear_sesion_http():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': '*/*'
    })
    return session

def obtener_url_dinamica(session, var_folder):
    """
    Escanea las corridas de la ruta /weather/nwp/icon-eu/grib/ para encontrar el .grib2.bz2 más reciente.
    """
    corridas = ["00", "03", "06", "09", "12", "15", "18", "21"]
    
    # Probamos desde la corrida más reciente hacia la más antigua
    for corrida in reversed(corridas):
        url_folder = f"{URL_BASE_NWP}/{corrida}/{var_folder}/"
        try:
            print(f"Escaneando carpeta DWD: {url_folder}")
            resp = session.get(url_folder, timeout=10)
            if resp.status_code == 200:
                # Buscar enlaces a archivos .grib2.bz2
                patron = r'href=["\']([^"\']+\.grib2\.bz2)["\']'
                archivos = re.findall(patron, resp.text, re.IGNORECASE)
                
                if archivos:
                    # Nos quedamos con el primer paso de predicción disponible (_000_) o el primero de la lista
                    archivos_paso0 = [f for f in archivos if "_000_" in f]
                    archivo_elegido = archivos_paso0[0] if archivos_paso0 else archivos[0]
                    
                    url_completa = url_folder + archivo_elegido
                    print(f"  -> ¡Archivo encontrado!: {archivo_elegido}")
                    return url_completa
        except Exception as e:
            print(f"  -> Error buscando en corrida {corrida}: {e}")
            
    raise RuntimeError(f"No se pudo encontrar ningún archivo válido en DWD para {var_folder}")

def descargar_y_descomprimir(session, url, file_bz2, file_grib):
    print(f"Descargando {url}...")
    resp = session.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    
    with open(file_bz2, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                
    print(f"Descomprimiendo {file_bz2} -> {file_grib}...")
    with bz2.BZ2File(file_bz2, 'rb') as source, open(file_grib, 'wb') as target:
        target.write(source.read())
    
    if os.path.exists(file_bz2):
        os.remove(file_bz2)

FILE_U_GRIB = "u10.grib2"
FILE_V_GRIB = "v10.grib2"
JSON_OUTPUT = "viento-espana.json"

try:
    session = crear_sesion_http()

    # 'u_10m' y 'v_10m' son los nombres exactos de carpeta en el servidor DWD NWP
    url_u = obtener_url_dinamica(session, "u_10m")
    url_v = obtener_url_dinamica(session, "v_10m")

    descargar_y_descomprimir(session, url_u, "u10.grib2.bz2", FILE_U_GRIB)
    descargar_y_descomprimir(session, url_v, "v10.grib2.bz2", FILE_V_GRIB)

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
