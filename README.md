# mapa-viento

Mapa de viento de España a partir del modelo **ICON-EU** del DWD (Deutscher
Wetterdienst). Un workflow de GitHub Actions descarga los datos cada 6 horas,
los recorta a la Península Ibérica y publica `viento-espana.json`.

## Qué hace

1. Descarga de [opendata.dwd.de](https://opendata.dwd.de/weather/nwp/icon-eu/grib/)
   los componentes **U** y **V** del viento a 10 m (`u_10m`, `v_10m`) de la
   corrida más reciente disponible.
2. Los descomprime (`.bz2`) y los lee con `xarray` / `cfgrib`.
3. Recorta a la bbox de España e Iberia:

   | | |
   |---|---|
   | latitud | 35,0 → 44,5 |
   | longitud | −10,0 → 4,5 |
   | resolución | 0,0625° → 233 × 153 = 35 649 puntos |
   | paso | 000 (análisis, condiciones actuales) |

4. Escribe `viento-espana.json`, un array con dos elementos: el componente U y
   el componente V, uno por registro, en una rejilla regular.

## Uso

```bash
pip install -r requirements.txt
python generar_viento_icon.py
```

En Linux hace falta una dependencia de sistema para leer GRIB2:

```bash
sudo apt-get install -y libeccodes-dev libeccodes-tools
```

El script escribe `viento-espana.json` en el directorio actual y borra los
`.grib2` intermedios.

## Formato de `viento-espana.json`

Array de dos posiciones: `[componente U, componente V]`.

```json
[
  {
    "header": {
      "parameterCategory": 2,
      "parameterNumber": 2,
      "nx": 233,
      "ny": 153,
      "basicAngle": 0,
      "subCenter": 0,
      "lo1": -10.0,
      "la1": 44.5,
      "lo2": 4.5,
      "la2": 35.0,
      "dx": 0.0625,
      "dy": 0.0625
    },
    "data": [-3.4622, -3.5081, "..."]
  },
  {
    "header": { "parameterNumber": 3 },
    "data": ["..."]
  }
]
```

- `data` está **aplanado** (fila a fila), con `nx * ny` valores en m/s.
- `lo1`/`la1` es la esquina superior izquierda; `lo2`/`la2` la inferior
  derecha.
- Las celdas sin dato del modelo se escriben como `0.0` (`np.nan_to_num`);
  no se distinguen de viento en calma.
- El JSON **no incluye** la fecha de la corrida ni el paso. Sólo se sabe por
  el historial de commits o por los logs del workflow.

### Velocidad y dirección

El JSON sólo trae U y V. Para la velocidad y la dirección:

```js
const speed = Math.hypot(u, v);                 // m/s
const dir = (Math.atan2(u, v) * 180 / Math.PI + 180) % 360; // grados, de dónde viene
```

Nota: la convención de dirección (`atan2(-u,-v)` frente a `atan2(u,v)`)
depende de si se quiere "hacia dónde va" o "de dónde viene"; compruébala
frente a un mapa conocido antes de usarla.

## Workflow

`.github/workflows/actualizar_viento.yml` se ejecuta con `cron: '30 */6 * * *'`
(cada 6 h) y también a mano con *workflow_dispatch*. Si el JSON generado es
idéntico al último commit, no hace commit.

## Desarrollo

```bash
# Sólo la lógica de selección de corrida (sin red, sin depender de xarray)
python -m unittest test_icon_utils

# Comparar la lógica nueva y la antigua contra el servidor DWD real
python verificar_dwd.py
```

- `generar_viento_icon.py` — descarga y procesa los GRIB.
- `icon_utils.py` — selección de corrida (funciones puras).
- `test_icon_utils.py` — pruebas unitarias.
- `verificar_dwd.py` — diagnóstico contra el servidor real.

## Fuente de datos

DWD Open Data, modelo ICON-EU. Los datos tienen licencia propia del DWD
(ver su página de *Open Data*); este repositorio sólo los redistribuye
procesados.
