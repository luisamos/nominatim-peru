#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geocodifica DATOS.xlsx usando Nominatim local.
Extrae TODOS los campos que retorna el servicio:
  - Campos base: place_id, osm_type, osm_id, lat, lon, display_name, class, type, importance, boundingbox
  - addressdetails: house_number, road, suburb, neighbourhood, city_district, city,
                    county, state, postcode, country, country_code, region, village, town, etc.
  - extratags:      wikipedia, wikidata, website, population, opening_hours, etc.
  - namedetails:    name, name:es, name:en, alt_name, official_name, etc.
"""
import argparse
import json
import time
from pathlib import Path
from collections import Counter

import pandas as pd
import requests
from tqdm import tqdm


# ── Campos base siempre presentes ──────────────────────────────────────────────
BASE_FIELDS = [
    "place_id", "osm_type", "osm_id",
    "lat", "lon",
    "display_name",
    "class", "type", "importance",
    "place_rank", "address_rank",
    "boundingbox",          # lista [lat_min, lat_max, lon_min, lon_max]
    "licence",
]

# ── Subcampos de addressdetails más comunes en Perú ────────────────────────────
ADDRESS_FIELDS = [
    "house_number", "road", "pedestrian", "path",
    "neighbourhood", "suburb", "quarter",
    "city_district", "district",
    "city", "town", "village", "municipality",
    "county", "state_district", "state", "region",
    "postcode", "country", "country_code",
]

# ── Subcampos de extratags útiles ──────────────────────────────────────────────
EXTRA_FIELDS = [
    "wikipedia", "wikidata", "website",
    "population", "opening_hours",
    "wheelchair", "phone", "email",
    "description",
]

# ── Subcampos de namedetails ───────────────────────────────────────────────────
NAME_FIELDS = [
    "name", "name:es", "name:en", "name:qu",
    "alt_name", "official_name", "short_name",
]


def limpiar(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip().upper()


def construir_consulta(row):
    """
    Formato óptimo para Nominatim Perú:
      DIRECCIÓN, DISTRITO, PROVINCIA, DEPARTAMENTO, Perú
    """
    partes = [
        limpiar(row.get("DIRECCIÓN", "")),
        limpiar(row.get("DISTRITO", "")),
        limpiar(row.get("PROVINCIA", "")),
        limpiar(row.get("DEPARTAMENTO", "")),
        "Perú",
    ]
    return ", ".join([p for p in partes if p])


def buscar_nominatim(session, base_url, query, timeout=30):
    url = base_url.rstrip("/") + "/search"
    params = {
        "q":             query,
        "format":        "jsonv2",   # más completo que json simple
        "limit":         1,
        "countrycodes":  "pe",
        "addressdetails": 1,         # desglose de dirección
        "extratags":     1,          # wikipedia, wikidata, population, etc.
        "namedetails":   1,          # nombres alternativos
        "accept-language": "es",     # preferir nombres en español
    }
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


def aplanar_resultado(result):
    """
    Convierte el JSON anidado de Nominatim en un dict plano
    con prefijos: addr__, extra__, name__
    """
    flat = {}

    # Campos base
    for f in BASE_FIELDS:
        val = result.get(f, "")
        if isinstance(val, list):
            val = "|".join(val)   # boundingbox como string separado por |
        flat[f] = val

    # addressdetails → prefijo addr__
    address = result.get("address", {}) or {}
    for f in ADDRESS_FIELDS:
        flat[f"addr__{f}"] = address.get(f, "")
    # Guardar también el JSON completo por si hay campos inesperados
    flat["address_json"] = json.dumps(address, ensure_ascii=False)

    # extratags → prefijo extra__
    extratags = result.get("extratags", {}) or {}
    for f in EXTRA_FIELDS:
        flat[f"extra__{f}"] = extratags.get(f, "")
    flat["extratags_json"] = json.dumps(extratags, ensure_ascii=False)

    # namedetails → prefijo name__
    namedetails = result.get("namedetails", {}) or {}
    for f in NAME_FIELDS:
        flat[f"name__{f}"] = namedetails.get(f, "")
    flat["namedetails_json"] = json.dumps(namedetails, ensure_ascii=False)

    return flat


def main():
    parser = argparse.ArgumentParser(description="Geocodificar DATOS.xlsx con Nominatim local")
    parser.add_argument("--input",      default="DATOS.xlsx",             help="Archivo Excel de entrada")
    parser.add_argument("--output",     default="DATOS_COORDENADAS.xlsx", help="Archivo Excel de salida")
    parser.add_argument("--sheet",      default="Hoja1",                  help="Nombre de hoja")
    parser.add_argument("--url",        default="http://localhost:8080",   help="URL base de Nominatim local")
    parser.add_argument("--sleep",      type=float, default=0.15,         help="Pausa entre consultas (s)")
    parser.add_argument("--max",        type=int,   default=0,            help="Máximo de filas; 0 = todas")
    parser.add_argument("--save-every", type=int,   default=100,          help="Guardar progreso cada N filas")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"No existe: {input_path}")

    df = pd.read_excel(input_path, sheet_name=args.sheet, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    required = ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "DIRECCIÓN"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}\nEncontradas: {list(df.columns)}")

    # Construir consultas
    df["CONSULTA_NOMINATIM"] = df.apply(construir_consulta, axis=1)

    # Pre-crear TODAS las columnas de salida con valor vacío
    all_output_cols = (
        ["ESTADO"]
        + BASE_FIELDS
        + [f"addr__{f}" for f in ADDRESS_FIELDS] + ["address_json"]
        + [f"extra__{f}" for f in EXTRA_FIELDS]  + ["extratags_json"]
        + [f"name__{f}" for f in NAME_FIELDS]    + ["namedetails_json"]
    )
    for col in all_output_cols:
        df[col] = ""

    total = len(df) if args.max <= 0 else min(args.max, len(df))
    stats = Counter()

    session = requests.Session()
    session.headers.update({"User-Agent": "geocodificador-local/1.0"})

    with tqdm(total=total, unit="dir", colour="green",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:

        for i in range(total):
            query = df.at[i, "CONSULTA_NOMINATIM"].strip()

            if not query:
                estado = "SIN CONSULTA"
            else:
                try:
                    result = buscar_nominatim(session, args.url, query)
                    if result is None:
                        estado = "NO ENCONTRADO"
                    else:
                        flat = aplanar_resultado(result)
                        for col, val in flat.items():
                            if col in df.columns:
                                df.at[i, col] = val
                        estado = "OK"
                except Exception as e:
                    estado = f"ERROR: {type(e).__name__}: {e}"

            df.at[i, "ESTADO"] = estado
            stats[estado] += 1

            pbar.set_postfix({
                "✓ OK":     stats["OK"],
                "✗ no_enc": stats["NO ENCONTRADO"],
                "⚠ err":    sum(v for k, v in stats.items() if k.startswith("ERROR")),
            }, refresh=False)
            pbar.set_description(f"{query[:50]:<50}", refresh=False)
            pbar.update(1)

            if args.save_every > 0 and (i + 1) % args.save_every == 0:
                df.to_excel(args.output, index=False)

            time.sleep(args.sleep)

    df.to_excel(args.output, index=False)

    print(f"\n{'─'*50}")
    print(f"  Total procesado  : {total}")
    print(f"  OK               : {stats['OK']}")
    print(f"  No encontrado    : {stats['NO ENCONTRADO']}")
    print(f"  Sin consulta     : {stats['SIN CONSULTA']}")
    errores = sum(v for k, v in stats.items() if k.startswith("ERROR"))
    if errores:
        print(f"  Errores          : {errores}")
    print(f"  Archivo salida   : {args.output}")
    print(f"{'─'*50}")


if __name__ == "__main__":
    main()