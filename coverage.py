"""
Filtro por cobertura. Lee coverage.csv y se queda solo con los hechos de las
empresas que cubrimos. El match por defecto es por razon social (normalizada,
sin tildes ni mayusculas) usando substring, que es robusto ante variaciones
chicas en como la SMV escribe el nombre. Si mas adelante cargas los RUC en el
CSV, se puede matchear por RUC que es aun mas exacto.
"""
import csv
import unicodedata

import config


def _norm(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def cargar_cobertura() -> list[dict]:
    with open(config.COVERAGE_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def filtrar_por_cobertura(hechos: list) -> list:
    cobertura = cargar_cobertura()
    # claves de match normalizadas
    razones = [(_norm(c["razon_social"]), c["razon_social"]) for c in cobertura]

    resultado = []
    for h in hechos:
        emp_norm = _norm(h.empresa)
        for razon_norm, razon_original in razones:
            if razon_norm and (razon_norm in emp_norm or emp_norm in razon_norm):
                resultado.append(h)
                break
    return resultado
