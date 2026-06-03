#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import time
from pathlib import Path
from collections import Counter

import pandas as pd
import requests


BASE_FIELDS = [
    "place_id", "osm_type", "osm_id",
    "lat", "lon",
    "display_name",
    "class", "type", "importance",
    "place_rank", "address_rank",
    "boundingbox",
    "licence",
]

ADDRESS_FIELDS = [
    "house_number", "road", "pedestrian", "path",
    "neighbourhood", "suburb", "quarter",
    "city_district", "district",
    "city", "town", "village", "municipality",
    "county", "state_district", "state", "region",
    "postcode", "country", "country_code",
]

EXTRA_FIELDS = [
    "wikipedia", "wikidata", "website",
    "population", "opening_hours",
    "wheelchair", "phone", "email",
    "description",
]

NAME_FIELDS = [
    "name", "name:es", "name:en", "name:qu",
    "alt_name", "official_name", "short_name",
]


def limpiar(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip().upper()


def construir_consulta(row):
    direccion = row.get("DIRECCIÓN", row.get("DIRECCION", ""))

    partes = [
        limpiar(direccion),
        limpiar(row.get("DISTRITO", "")),
        limpiar(row.get("PROVINCIA", "")),
        limpiar(row.get("DEPARTAMENTO", "")),
        "Perú",
    ]

    return ", ".join([p for p in partes if p])


def guardar_estado(progress_file, data):
    Path(progress_file).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def leer_archivo(input_path, sheet):
    input_path = Path(input_path)
    ext = input_path.suffix.lower()

    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(input_path, sheet_name=sheet, dtype=str)

    if ext == ".csv":
        return pd.read_csv(input_path, dtype=str, encoding="utf-8-sig")

    raise ValueError("Formato no soportado. Usa CSV, XLSX o XLS.")


def buscar_nominatim(session, base_url, query, timeout=30):
    url = base_url.rstrip("/") + "/search"

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "pe",
        "addressdetails": 1,
        "extratags": 1,
        "namedetails": 1,
        "accept-language": "es",
    }

    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()

    data = r.json()
    return data[0] if data else None


def aplanar_resultado(result):
    flat = {}

    for f in BASE_FIELDS:
        val = result.get(f, "")
        if isinstance(val, list):
            val = "|".join(val)
        flat[f] = val

    address = result.get("address", {}) or {}
    for f in ADDRESS_FIELDS:
        flat[f"addr__{f}"] = address.get(f, "")
    flat["address_json"] = json.dumps(address, ensure_ascii=False)

    extratags = result.get("extratags", {}) or {}
    for f in EXTRA_FIELDS:
        flat[f"extra__{f}"] = extratags.get(f, "")
    flat["extratags_json"] = json.dumps(extratags, ensure_ascii=False)

    namedetails = result.get("namedetails", {}) or {}
    for f in NAME_FIELDS:
        flat[f"name__{f}"] = namedetails.get(f, "")
    flat["namedetails_json"] = json.dumps(namedetails, ensure_ascii=False)

    return flat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--sheet", default="Hoja1")
    parser.add_argument("--url", default="http://localhost")
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument("--save-every", type=int, default=100)
    args = parser.parse_args()

    stats = Counter()

    try:
        guardar_estado(args.progress, {
            "estado": "INICIANDO",
            "mensaje": "Leyendo archivo de entrada",
            "total": 0,
            "procesados": 0,
            "ok": 0,
            "no_encontrado": 0,
            "errores": 0,
            "porcentaje": 0
        })

        df = leer_archivo(args.input, args.sheet)
        df.columns = [str(c).strip().upper() for c in df.columns]

        required = ["DEPARTAMENTO", "PROVINCIA", "DISTRITO"]

        if "DIRECCIÓN" not in df.columns and "DIRECCION" not in df.columns:
            required.append("DIRECCIÓN")

        missing = [c for c in required if c not in df.columns]

        if missing:
            raise ValueError(f"Faltan columnas: {missing}. Columnas encontradas: {list(df.columns)}")

        df["CONSULTA_NOMINATIM"] = df.apply(construir_consulta, axis=1)

        all_output_cols = (
            ["ESTADO"]
            + BASE_FIELDS
            + [f"addr__{f}" for f in ADDRESS_FIELDS] + ["address_json"]
            + [f"extra__{f}" for f in EXTRA_FIELDS] + ["extratags_json"]
            + [f"name__{f}" for f in NAME_FIELDS] + ["namedetails_json"]
        )

        for col in all_output_cols:
            if col not in df.columns:
                df[col] = ""

        total = len(df)

        session = requests.Session()
        session.headers.update({
            "User-Agent": "geocodificador-local-web/1.0"
        })

        guardar_estado(args.progress, {
            "estado": "PROCESANDO",
            "mensaje": "Iniciando geocodificación",
            "total": total,
            "procesados": 0,
            "ok": 0,
            "no_encontrado": 0,
            "errores": 0,
            "porcentaje": 0
        })

        for i in range(total):
            query = str(df.at[i, "CONSULTA_NOMINATIM"]).strip()

            try:
                if not query:
                    estado = "SIN CONSULTA"
                else:
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

            procesados = i + 1
            errores = sum(v for k, v in stats.items() if k.startswith("ERROR"))
            porcentaje = round((procesados / total) * 100, 2)

            guardar_estado(args.progress, {
                "estado": "PROCESANDO",
                "mensaje": query[:120],
                "total": total,
                "procesados": procesados,
                "ok": stats["OK"],
                "no_encontrado": stats["NO ENCONTRADO"],
                "sin_consulta": stats["SIN CONSULTA"],
                "errores": errores,
                "porcentaje": porcentaje
            })

            if args.save_every > 0 and procesados % args.save_every == 0:
                df.to_excel(args.output, index=False)

            time.sleep(args.sleep)

        df.to_excel(args.output, index=False)

        guardar_estado(args.progress, {
            "estado": "FINALIZADO",
            "mensaje": "Proceso terminado correctamente",
            "total": total,
            "procesados": total,
            "ok": stats["OK"],
            "no_encontrado": stats["NO ENCONTRADO"],
            "sin_consulta": stats["SIN CONSULTA"],
            "errores": sum(v for k, v in stats.items() if k.startswith("ERROR")),
            "porcentaje": 100,
            "archivo_salida": str(args.output)
        })

    except Exception as e:
        guardar_estado(args.progress, {
            "estado": "ERROR",
            "mensaje": f"{type(e).__name__}: {e}",
            "total": 0,
            "procesados": 0,
            "ok": 0,
            "no_encontrado": 0,
            "errores": 1,
            "porcentaje": 0
        })


if __name__ == "__main__":
    main()