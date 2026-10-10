"""Pruebas de la selección de corrida.

Sin red: sólo se prueban nombres de fichero. Ejecutar con:

    python -m unittest test_icon_utils
"""

import unittest

from icon_utils import elegir_archivo_mas_reciente, paso, run_stamp


def nombre(sello, paso_):
    return f"icon-eu_europe_regular-lat-lon_single-level_{sello}_{paso_:03d}_U_10M.grib2.bz2"


def nombre_v(sello, paso_):
    return f"icon-eu_europe_regular-lat-lon_single-level_{sello}_{paso_:03d}_V_10M.grib2.bz2"


RUN_AYER = "2026100921"   # lo que había en la carpeta 21
RUN_HOY = "2026101000"    # lo que ya había en la carpeta 00


class RunStampTest(unittest.TestCase):
    def test_extrae_sello(self):
        self.assertEqual(run_stamp(nombre(RUN_HOY, 0)), RUN_HOY)

    def test_componente_v(self):
        self.assertEqual(run_stamp(nombre_v(RUN_HOY, 4)), RUN_HOY)

    def test_nombre_ajeno_devuelve_none(self):
        self.assertIsNone(run_stamp("index.html"))
        self.assertIsNone(run_stamp(""))
        self.assertIsNone(run_stamp(None))


class PasoTest(unittest.TestCase):
    def test_extrae_paso(self):
        self.assertEqual(paso(nombre(RUN_HOY, 7)), 7)

    def test_nombre_ajeno_devuelve_none(self):
        self.assertIsNone(paso("README.md"))


class ElegirArchivoTest(unittest.TestCase):
    def test_elige_corrida_mas_reciente_aunque_la_carpeta_sea_anterior(self):
        """El caso medido el 2026-10-10: '21' tenía ayer, '00' ya tenía hoy."""
        archivos = [nombre(RUN_AYER, p) for p in (0, 1, 2)]
        archivos += [nombre(RUN_HOY, p) for p in (0, 1, 2)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_HOY, 0))

    def test_prefiere_paso_cero(self):
        archivos = [nombre(RUN_HOY, 5), nombre(RUN_HOY, 0), nombre(RUN_HOY, 3)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_HOY, 0))

    def test_sin_paso_cero_en_ninguna_corrida_cae_al_paso_mas_bajo_de_la_reciente(self):
        archivos = [nombre(RUN_HOY, 30), nombre(RUN_HOY, 12)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_HOY, 12))

    def test_prefiere_analisis_antiguo_antes_que_paso_tardio_de_corrida_nueva(self):
        """Si la corrida nueva aún no tiene el paso 000, vale más el análisis
        completo de la corrida anterior que un paso tardío de la nueva."""
        archivos = [nombre(RUN_AYER, 0), nombre(RUN_HOY, 30)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_AYER, 0))

    def test_ignora_nombres_no_reconocibles(self):
        archivos = ["index.html", "..", nombre(RUN_AYER, 0)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_AYER, 0))

    def test_mezcla_componentes_u_y_v(self):
        archivos = [nombre_v(RUN_AYER, 0), nombre(RUN_HOY, 0)]
        self.assertEqual(elegir_archivo_mas_reciente(archivos), nombre(RUN_HOY, 0))

    def test_lista_vacia_devuelve_none(self):
        self.assertIsNone(elegir_archivo_mas_reciente([]))
        self.assertIsNone(elegir_archivo_mas_reciente(None))

    def test_solo_nombres_ajenos_devuelve_none(self):
        self.assertIsNone(elegir_archivo_mas_reciente(["a.txt", "b.gz"]))


if __name__ == "__main__":
    unittest.main()
