"""
Prueba rapida (smoke test).

Prueba la mitad del pipeline que NO depende del scraper: filtro por cobertura +
clasificacion con IA + digest, usando hechos de EJEMPLO (inventados). Sirve para:
  - confirmar de una que tu ANTHROPIC_API_KEY funciona,
  - ver como queda el digest,
sin tener que hacer funcionar primero los selectores del scraper.

Correr:  python probar.py
"""
import scraper   # solo para reusar la dataclass Hecho
import coverage
import classifier
import digest


# Hechos de EJEMPLO (inventados) para probar el flujo sin scrapear la SMV.
EJEMPLOS = [
    scraper.Hecho(empresa="ALICORP S.A.A.", fecha="16/07/2026", hora="09:00", fecha_publicacion="16/07/2026", codigo="L14",
                  tipo="L14 Distribucion de utilidades",
                  descripcion="El directorio aprobo el reparto de un dividendo en efectivo.",
                  url_documento="https://www.smv.gob.pe/ejemplo"),
    scraper.Hecho(empresa="FERREYCORP S.A.A.", fecha="16/07/2026", hora="09:00", fecha_publicacion="16/07/2026", codigo="L10",
                  tipo="L10 Informacion financiera",
                  descripcion="Se publican los estados financieros del segundo trimestre 2026.",
                  url_documento="https://www.smv.gob.pe/ejemplo"),
    scraper.Hecho(empresa="EMPRESA QUE NO CUBRIMOS S.A.", fecha="16/07/2026", hora="09:00", fecha_publicacion="16/07/2026", codigo="L01",
                  tipo="L01 Convocatoria a junta",
                  descripcion="Convocatoria a junta general de accionistas.",
                  url_documento=""),
    scraper.Hecho(empresa="ENGIE ENERGIA PERU S.A.", fecha="16/07/2026", hora="09:00", fecha_publicacion="16/07/2026", codigo="L40",
                  tipo="L40 Posicion mensual de derivados",
                  descripcion="Reporte de posicion mensual en instrumentos financieros derivados.",
                  url_documento=""),
]


def main():
    print("== 1) Filtro por cobertura ==")
    de_cobertura = coverage.filtrar_por_cobertura(EJEMPLOS)
    for h in EJEMPLOS:
        marca = "SI" if h in de_cobertura else "no"
        print(f"  [{marca}] {h.empresa}")
    print(f"  -> {len(de_cobertura)} de {len(EJEMPLOS)} pasaron el filtro\n")

    print("== 2) Clasificacion con IA (llamada real a la API) ==")
    clasificados = classifier.clasificar_todos(de_cobertura)
    print("  OK, la API respondio.\n")

    print("== 3) Digest ==\n")
    digest.entregar(clasificados)


if __name__ == "__main__":
    main()
