#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geocodifica direcciones de DEMO-MAPEO.xlsx usando un Nominatim local.
Columnas esperadas: DEPARTAMENTO, PROVINCIA, DISTRITO, DIRECCIÓN.
Salida: Excel con CONSULTA_NOMINATIM, LATITUD, LONGITUD, DISPLAY_NAME, ESTADO.
"""
import argparse
import time
from pathlib import Path
from collections import Counter

import pandas as pd
import requests
from tqdm import tqdm


def limpiar(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def construir_consulta(row):
    partes = [
        limpiar(row.get("DIRECCIÓN")),
        limpiar(row.get("DISTRITO")),
        limpiar(row.get("PROVINCIA")),
        limpiar(row.get("DEPARTAMENTO")),
        "Perú",
    ]
    return ", ".join([p for p in partes if p])


def buscar_nominatim(session, base_url, query, timeout=30):
    url = base_url.rstrip("/") + "/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "pe",
        "addressdetails": 1,
    }
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    return data[0]


def main():
    parser = argparse.ArgumentParser(description="Geocodificar Excel con Nominatim local")
    parser.add_argument("--input",  default="DEMO-MAPEO.xlsx",             help="Archivo Excel de entrada")
    parser.add_argument("--output", default="DEMO-MAPEO_COORDENADAS.xlsx", help="Archivo Excel de salida")
    parser.add_argument("--sheet",  default="Hoja1",                       help="Nombre de hoja")
    parser.add_argument("--url",    default="http://localhost:8080",        help="URL base de Nominatim local")
    parser.add_argument("--sleep",  type=float, default=0.15,              help="Pausa entre consultas (s)")
    parser.add_argument("--max",    type=int,   default=0,                 help="Máximo de filas; 0 = todas")
    parser.add_argument("--save-every", type=int, default=100,             help="Guardar progreso cada N filas")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {input_path}")

    df = pd.read_excel(input_path, sheet_name=args.sheet, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    required = ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "DIRECCIÓN"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}. Encontradas: {list(df.columns)}")

    if "CONSULTA_NOMINATIM" not in df.columns:
        df["CONSULTA_NOMINATIM"] = df.apply(construir_consulta, axis=1)
    for col in ["LATITUD", "LONGITUD", "DISPLAY_NAME", "ESTADO"]:
        if col not in df.columns:
            df[col] = ""

    total = len(df) if args.max <= 0 else min(args.max, len(df))
    stats = Counter()

    session = requests.Session()
    session.headers.update({"User-Agent": "geocodificador-local-luis/1.0"})

    with tqdm(total=total, unit="dir", colour="green",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:

        for i in range(total):
            query = limpiar(df.at[i, "CONSULTA_NOMINATIM"])

            if not query:
                estado = "SIN CONSULTA"
            else:
                try:
                    result = buscar_nominatim(session, args.url, query)
                    if result is None:
                        estado = "NO ENCONTRADO"
                    else:
                        df.at[i, "LATITUD"]      = result.get("lat", "")
                        df.at[i, "LONGITUD"]     = result.get("lon", "")
                        df.at[i, "DISPLAY_NAME"] = result.get("display_name", "")
                        estado = "OK"
                except Exception as e:
                    estado = f"ERROR: {type(e).__name__}"

            df.at[i, "ESTADO"] = estado
            stats[estado] += 1

            # Actualizar descripción con contadores en tiempo real
            pbar.set_postfix({
                "OK": stats["OK"],
                "no_enc": stats["NO ENCONTRADO"],
                "err": sum(v for k, v in stats.items() if k.startswith("ERROR")),
            }, refresh=False)
            pbar.set_description(f"{query[:45]:<45}", refresh=False)
            pbar.update(1)

            # Guardado parcial para no perder trabajo en cortes largos
            if args.save_every > 0 and (i + 1) % args.save_every == 0:
                df.to_excel(args.output, index=False)

            time.sleep(args.sleep)

    df.to_excel(args.output, index=False)

    # Resumen final
    print(f"\n{'─'*45}")
    print(f"  Total procesado : {total}")
    print(f"  OK              : {stats['OK']}")
    print(f"  No encontrado   : {stats['NO ENCONTRADO']}")
    print(f"  Sin consulta    : {stats['SIN CONSULTA']}")
    errores = sum(v for k, v in stats.items() if k.startswith("ERROR"))
    if errores:
        print(f"  Errores         : {errores}")
    print(f"  Archivo salida  : {args.output}")
    print(f"{'─'*45}")


if __name__ == "__main__":
    main()