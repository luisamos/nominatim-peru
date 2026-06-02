# Guía de instalación y ejecución del script de geocodificación con Nominatim local

Esta guía describe cómo instalar las dependencias necesarias y ejecutar el script `geocodificar_nominatim.py` para obtener coordenadas a partir de direcciones almacenadas en un archivo Excel, usando un servicio local de Nominatim.

---

## 1. Requisitos previos

Antes de ejecutar el script, debes tener:

- Ubuntu Server o una distribución compatible.
- Nominatim instalado.
- Base de datos de Perú importada en Nominatim.
- Servicio web de Nominatim levantado en `http://localhost:8080`.
- Archivo Excel de entrada:
  - `DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx`
- Script Python:
  - `geocodificar_nominatim.py`

---

## 2. Ubicación recomendada de archivos

Se recomienda trabajar en el directorio del proyecto de Nominatim:

```bash
cd /data/osm
```

Verifica que existan los archivos:

```bash
ls -lh
```

Debes ver archivos similares a:

```text
DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx
geocodificar_nominatim.py
```

---

## 3. Instalar dependencias de Python

Debido a que el servidor puede tener problemas SSL con `pip`, se recomienda instalar las librerías desde `apt`.

Ejecuta:

```bash
sudo apt update
sudo apt install -y python3-pandas python3-requests python3-openpyxl
```

Verifica que las librerías estén instaladas correctamente:

```bash
python3 -c "import pandas, requests, openpyxl; print('LIBRERIAS OK')"
```

Si todo está correcto, debe mostrar:

```text
LIBRERIAS OK
```

---

## 4. Levantar el servicio web de Nominatim

En una terminal, ejecuta:

```bash
cd /data/osm/website
php -S 0.0.0.0:8080
```

El servicio quedará disponible en:

```text
http://localhost:8080
```

No cierres esta terminal mientras estés geocodificando.

---

## 5. Probar que Nominatim responde

Abre otra terminal y ejecuta:

```bash
curl "http://localhost:8080/search?q=Lima&format=json"
```

Si devuelve una respuesta en formato JSON, el servicio está funcionando correctamente.

También puedes probar:

```bash
curl "http://localhost:8080/search?q=Trujillo,%20La%20Libertad,%20Peru&format=json"
```

---

## 6. Ejecutar una prueba con pocas filas

Antes de procesar todo el Excel, se recomienda ejecutar una prueba con 10 registros.

```bash
cd /data/osm

python3 geocodificar_nominatim.py \
  --input DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx \
  --output DEMO-MAPEO_COORDENADAS_PRUEBA.xlsx \
  --url http://localhost:8080 \
  --max 10
```

Al finalizar, debe generarse el archivo:

```text
DEMO-MAPEO_COORDENADAS_PRUEBA.xlsx
```

Verifica el archivo:

```bash
ls -lh DEMO-MAPEO_COORDENADAS_PRUEBA.xlsx
```

---

## 7. Ejecutar el procesamiento completo

Si la prueba fue correcta, ejecuta el procesamiento completo:

```bash
cd /data/osm

python3 geocodificar_nominatim.py \
  --input DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx \
  --output DEMO-MAPEO_COORDENADAS_FINAL.xlsx \
  --url http://localhost:8080
```

El resultado final será:

```text
DEMO-MAPEO_COORDENADAS_FINAL.xlsx
```

---

## 8. Columnas esperadas en el resultado

El archivo de salida debe contener las columnas originales del Excel y columnas adicionales como:

```text
CONSULTA_NOMINATIM
LATITUD
LONGITUD
DISPLAY_NAME
ESTADO
```

Descripción:

| Campo                | Descripción                                               |
| -------------------- | --------------------------------------------------------- |
| `CONSULTA_NOMINATIM` | Texto usado para consultar en Nominatim.                  |
| `LATITUD`            | Coordenada de latitud encontrada.                         |
| `LONGITUD`           | Coordenada de longitud encontrada.                        |
| `DISPLAY_NAME`       | Nombre completo devuelto por Nominatim.                   |
| `ESTADO`             | Resultado del proceso: encontrado, no encontrado o error. |

---

## 9. Comando principal

El comando principal para ejecutar el script es:

```bash
python3 geocodificar_nominatim.py \
  --input DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx \
  --output DEMO-MAPEO_COORDENADAS_FINAL.xlsx \
  --url http://localhost:8080
```

---

## 10. Errores comunes

### Error: Nominatim no responde

Si aparece un error de conexión, verifica que el servicio esté levantado:

```bash
cd /data/osm/website
php -S 0.0.0.0:8080
```

Luego prueba:

```bash
curl "http://localhost:8080/search?q=Lima&format=json"
```

---

### Error: No module named pandas

Instala las dependencias:

```bash
sudo apt install -y python3-pandas python3-requests python3-openpyxl
```

---

### Error SSL al usar pip

Si aparece un error como:

```text
CERTIFICATE_VERIFY_FAILED
self-signed certificate in certificate chain
```

No uses `pip`. Instala las librerías desde `apt`:

```bash
sudo apt install -y python3-pandas python3-requests python3-openpyxl
```

---

### Direcciones no encontradas

Algunas direcciones pueden no devolver coordenadas si están incompletas, abreviadas o si no existen en OpenStreetMap.

Ejemplos de direcciones que pueden requerir limpieza:

```text
S/N
LTDA
APV
PPJJ
CARR
MZ
LT
```

En esos casos, se recomienda mejorar la dirección agregando distrito, provincia, departamento y país.

---

## 11. Recomendación operativa

Para mejores resultados, el Excel debe contener como mínimo:

```text
DEPARTAMENTO
PROVINCIA
DISTRITO
DIRECCIÓN
```

La búsqueda debe construirse combinando la dirección con su contexto territorial, por ejemplo:

```text
CALLE JOSE CARLOS MARIATEGUI 205, AYACUCHO, HUAMANGA, AYACUCHO, Perú
```

Esto mejora la precisión de la geocodificación.

---

## 12. Flujo recomendado

1. Levantar Nominatim:

```bash
cd /data/osm/website
php -S 0.0.0.0:8080
```

2. Probar Nominatim:

```bash
curl "http://localhost:8080/search?q=Lima&format=json"
```

3. Ejecutar prueba:

```bash
cd /data/osm

python3 geocodificar_nominatim.py \
  --input DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx \
  --output DEMO-MAPEO_COORDENADAS_PRUEBA.xlsx \
  --url http://localhost:8080 \
  --max 10
```

4. Ejecutar proceso final:

```bash
python3 geocodificar_nominatim.py \
  --input DEMO-MAPEO_CONSULTAS_COORDENADAS.xlsx \
  --output DEMO-MAPEO_COORDENADAS_FINAL.xlsx \
  --url http://localhost:8080
```

5. Revisar resultado:

```bash
ls -lh DEMO-MAPEO_COORDENADAS_FINAL.xlsx
```

---

## 13. Resultado esperado

Al finalizar el proceso, tendrás un archivo Excel llamado:

```text
DEMO-MAPEO_COORDENADAS_FINAL.xlsx
```

Este archivo contendrá las direcciones originales y sus coordenadas obtenidas desde tu Nominatim local.
