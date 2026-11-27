# Integración y preparación de datos abiertos para BI: egresos hospitalarios y población por cantón (Ecuador, 2023)

Proyecto bimestral 1 de **Introducción a la inteligencia de negocios**, Universidad Técnica Particular de Loja (UTPL).

- **Integrantes:** Lenin Correa, Fabian Cañar
- **Docente:** Ing. Ángel Eduardo Encalada Encalada
- **Fecha:** 27 de noviembre de 2026

## Necesidad de información

¿Qué cantones del Ecuador presentan más egresos hospitalarios por cada 1.000 habitantes en 2023?

Los egresos hospitalarios son conteos absolutos y dependen del tamaño de la población. Para compararlos entre cantones se integran con la población cantonal y se calcula una tasa por 1.000 habitantes.

## Fuentes de datos

Ambas fuentes son del Instituto Nacional de Estadística y Censos (INEC), de acceso público y con licencia Creative Commons Atribución 4.0 Internacional.

| Fuente | Archivo usado | Enlace |
| --- | --- | --- |
| Registro Estadístico de Camas y Egresos Hospitalarios 2023 | `egresos_hospitalarios_2023.csv` | https://www.ecuadorencifras.gob.ec/camas-y-egresos-hospitalarios-2023/ |
| Estimaciones y Proyecciones de Población, revisión 2024 | `Tabulado_cantonal_2010-2035_rev2024.xlsx` | https://www.ecuadorencifras.gob.ec/estimaciones-y-proyecciones-de-poblacion-revision-2024/ |

## Estructura del repositorio

```
.
├── datos_fuente/        Archivos originales descargados, sin modificar
├── scripts_etl/         Scripts del diagnóstico y del proceso ETL
├── datos_resultantes/   Conjunto de datos integrado
└── evidencias/          Capturas y registros del diagnóstico y de la validación
```

- `scripts_etl/etl_egresos_poblacion.py`: proceso ETL completo (extracción, transformación, integración, carga y validación).
- `datos_resultantes/egresos_poblacion_canton_2023.csv`: resultado integrado, con una fila por cantón y las columnas `provincia`, `canton`, `anio`, `egresos`, `poblacion` y `tasa_egresos_x1000`.
- `evidencias/`: capturas del diagnóstico de calidad, `diagnostico_calidad.txt` y `validacion_etl.txt` (registro de la ejecución del ETL).

## Resumen del proceso

1. **Extracción:** lectura del CSV de egresos (separador `;`, codificación `utf-8-sig`) y del Excel de población (una hoja por provincia).
2. **Transformación:** eliminación de 2.736 filas duplicadas, exclusión de 466 egresos con residencia en el exterior, agrupación por provincia y cantón de residencia, y normalización de nombres (minúsculas, sin tildes ni puntos).
3. **Integración:** unión por provincia y cantón normalizados, con un diccionario de equivalencias para 9 nombres que no coinciden entre fuentes (por ejemplo, `Quito` y `Distrito Metropolitano de Quito`).
4. **Carga:** escritura del CSV integrado en `datos_resultantes/`.
5. **Validación:** cuadre de egresos, ausencia de nulos, cobertura de la unión y coincidencia con los totales provinciales.

## Resultados principales

- 221 cantones en 24 provincias, sin valores nulos.
- 1.167.611 egresos integrados (1.168.077 tras eliminar duplicados, menos 466 del exterior).
- 0 cantones sin coincidencia entre fuentes tras aplicar el diccionario de equivalencias.
- La suma de la población de los cantones coincide con el total provincial del INEC.
- Tasa de egresos por 1.000 habitantes: media 57,11, mediana 52,21, mínimo 13,31 y máximo 141,72.

La tasa mide egresos por habitante, no personas distintas atendidas, y la población es una estimación al 30 de junio. Debe leerse como un indicador comparativo de uso de servicios hospitalarios.

## Cómo ejecutar el ETL

Requisitos: Python 3 con `pandas` y `openpyxl`.

```bash
pip install pandas openpyxl
python scripts_etl/etl_egresos_poblacion.py
```

El script busca los archivos de `datos_fuente/` a partir de su propia ubicación, así que puede ejecutarse desde cualquier carpeta. Tarda uno o dos minutos por el tamaño del CSV de egresos. Genera `datos_resultantes/egresos_poblacion_canton_2023.csv` y los registros en `evidencias/`.

## Archivos grandes (Git LFS)

Los archivos grandes de `datos_fuente/` (en particular el CSV de egresos, de unos 694 MB) están almacenados con **Git LFS**. Para obtenerlos:

- Descargarlos desde la página del archivo en GitHub, o
- Clonar el repositorio con Git LFS instalado:

```bash
git lfs install
git clone https://github.com/tinobest1/proyecto-bi-egresos-hospitalarios.git
```

## Propuesta de almacenamiento

Se propone un **Data Mart de salud** con un esquema en estrella: una tabla de hechos a nivel cantón y año (egresos, población y tasa) y dimensiones de territorio y tiempo. La propuesta completa está en el informe técnico.

## Fuentes y atribución

Datos del Instituto Nacional de Estadística y Censos (INEC), Ecuador, bajo licencia [Creative Commons Atribución 4.0 Internacional](http://creativecommons.org/licenses/by/4.0/).
