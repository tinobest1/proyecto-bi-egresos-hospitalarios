from pathlib import Path
import re
import unicodedata
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ANIO = 2023
ELIMINAR_DUPLICADOS = True   # decisión documentada en el informe

DIR_RESULTADOS = RAIZ / "datos_resultantes"
DIR_EVIDENCIAS = RAIZ / "evidencias"
DIR_RESULTADOS.mkdir(exist_ok=True)
DIR_EVIDENCIAS.mkdir(exist_ok=True)

# Nombres abreviados o distintos entre fuentes (ya normalizados)
# Nombres distintos entre fuentes (ya normalizados): egresos -> población
EQUIVALENCIAS = {
    "crnel marcelino mariduena": "coronel marcelino mariduena",
    "quito": "distrito metropolitano de quito",
    "empalme": "el empalme",
    "orellana": "francisco de orellana",
    "cotacahi": "cotacachi",                                   # errata en egresos
    "la condordia": "la concordia",                            # errata en egresos
    "gnral antonio elizalde": "general antonio elizalde",
    "carlos julio arrosemena tola": "carlos julio arosemena tola",
    "alfredo baquerizo moreno": "alfredo baquerizo moreno (jujan)",
}

registro = []
def log(msg=""):
    print(msg)
    registro.append(str(msg))

def normalizar(texto):
    """Minúsculas, sin tildes, sin puntos y sin espacios repetidos."""
    if pd.isna(texto):
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace(".", " ")
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------
# 1. EXTRACCIÓN
# ------------------------------------------------------------------
log("=== 1. EXTRACCIÓN ===")
ruta_egresos = next(RAIZ.rglob("egresos_hospitalarios_2023.csv"))
ruta_poblacion = next(RAIZ.rglob("Tabulado_cantonal_2010-2035_rev2024.xlsx"))

egresos = pd.read_csv(ruta_egresos, sep=";", encoding="utf-8-sig", low_memory=False)
n_original = len(egresos)
log(f"Egresos leídos: {n_original} filas, {egresos.shape[1]} columnas")

def leer_poblacion(xlsx):
    filas, totales = [], {}
    for hoja in pd.ExcelFile(xlsx).sheet_names:
        if hoja == "Indice":
            continue
        df = pd.read_excel(xlsx, sheet_name=hoja, header=None)
        num = df.apply(pd.to_numeric, errors="coerce")
        fila_enc = next(i for i in range(len(df)) if (num.iloc[i] == ANIO).any())
        col_anio = next(j for j in range(df.shape[1]) if num.iloc[fila_enc, j] == ANIO)
        datos = df.iloc[fila_enc + 1:, [1, col_anio]].copy()
        datos.columns = ["canton", "poblacion"]
        datos["poblacion"] = pd.to_numeric(datos["poblacion"], errors="coerce")
        datos = datos.dropna(subset=["canton", "poblacion"]).reset_index(drop=True)
        provincia = str(datos.loc[0, "canton"]).strip()   # primera fila = total provincial
        totales[provincia] = datos.loc[0, "poblacion"]
        cantones = datos.iloc[1:].copy()
        cantones["provincia"] = provincia
        filas.append(cantones)
    return pd.concat(filas, ignore_index=True), totales

poblacion, totales_prov = leer_poblacion(ruta_poblacion)
log(f"Población {ANIO}: {len(poblacion)} cantones en {poblacion['provincia'].nunique()} provincias")


# ------------------------------------------------------------------
# 2. TRANSFORMACIÓN
# ------------------------------------------------------------------
log("\n=== 2. TRANSFORMACIÓN ===")
for col in ["prov_res", "cant_res"]:
    egresos[col] = egresos[col].astype(str).str.strip()

n_dup = int(egresos.duplicated().sum())
log(f"Filas duplicadas completas: {n_dup}")
if ELIMINAR_DUPLICADOS:
    egresos = egresos.drop_duplicates()
    log(f"Duplicados eliminados. Filas restantes: {len(egresos)}")
n_tras_dup = len(egresos)

es_exterior = egresos["prov_res"].map(normalizar) == "exterior"
n_exterior = int(es_exterior.sum())
egresos = egresos[~es_exterior]
log(f"Egresos con residencia en el exterior (excluidos): {n_exterior}")

# Conteo de egresos por provincia y cantón de residencia
conteo = (egresos.groupby(["prov_res", "cant_res"], as_index=False)
                 .size().rename(columns={"size": "egresos"}))
conteo["canton_norm"] = conteo["cant_res"].map(normalizar).replace(EQUIVALENCIAS)
conteo["clave"] = conteo["prov_res"].map(normalizar) + "|" + conteo["canton_norm"]

poblacion["clave"] = (poblacion["provincia"].map(normalizar) + "|"
                      + poblacion["canton"].map(normalizar))
if poblacion["clave"].duplicated().any():
    log("AVISO: hay claves duplicadas en población")


# ------------------------------------------------------------------
# 3. INTEGRACIÓN
# ------------------------------------------------------------------
log("\n=== 3. INTEGRACIÓN ===")
unido = conteo.merge(
    poblacion[["clave", "provincia", "canton", "poblacion"]],
    on="clave", how="outer", indicator=True
)

sin_poblacion = unido[unido["_merge"] == "left_only"]
sin_egresos = unido[unido["_merge"] == "right_only"]
log(f"Cantones de egresos sin coincidencia en población: {len(sin_poblacion)} "
    f"({int(sin_poblacion['egresos'].sum())} egresos)")
log(f"Cantones de población sin egresos (se asigna 0): {len(sin_egresos)}")

sin_poblacion[["prov_res", "cant_res", "egresos"]].to_csv(
    DIR_EVIDENCIAS / "cantones_sin_coincidencia.csv", index=False, encoding="utf-8-sig")
if len(sin_poblacion):
    log(sin_poblacion[["prov_res", "cant_res", "egresos"]].to_string(index=False))

final = unido[unido["_merge"] != "left_only"].copy()
final["egresos"] = final["egresos"].fillna(0).astype(int)
final["anio"] = ANIO
final["tasa_egresos_x1000"] = (final["egresos"] / final["poblacion"] * 1000).round(2)
final = (final[["provincia", "canton", "anio", "egresos", "poblacion", "tasa_egresos_x1000"]]
         .sort_values(["provincia", "canton"]).reset_index(drop=True))


# ------------------------------------------------------------------
# 4. CARGA
# ------------------------------------------------------------------
log("\n=== 4. CARGA ===")
salida = DIR_RESULTADOS / "egresos_poblacion_canton_2023.csv"
final.to_csv(salida, index=False, encoding="utf-8-sig")
log(f"Guardado: {salida}")


# ------------------------------------------------------------------
# 5. VALIDACIÓN
# ------------------------------------------------------------------
log("\n=== 5. VALIDACIÓN ===")
total_final = int(final["egresos"].sum())
total_sin_match = int(sin_poblacion["egresos"].sum())
log(f"a) Egresos tras duplicados: {n_tras_dup} | exterior: {n_exterior} | "
    f"sin coincidencia: {total_sin_match} | integrados: {total_final}")
log(f"   ¿Suma cuadra? {n_exterior + total_sin_match + total_final == n_tras_dup}")

log(f"b) Filas del dataset integrado: {len(final)} | nulos: {int(final.isna().sum().sum())}")
log(f"c) Población mínima: {final['poblacion'].min()} (debe ser > 0)")

suma_cantones = final.groupby("provincia")["poblacion"].sum()
dif = max(abs(suma_cantones[p] - totales_prov[p]) for p in suma_cantones.index)
log(f"d) Máxima diferencia entre suma de cantones y total provincial: {dif}")

log("e) Estadísticos de la tasa por 1000 habitantes:")
log(final["tasa_egresos_x1000"].describe().round(2).to_string())
log("   Top 5 cantones por tasa:")
log(final.nlargest(5, "tasa_egresos_x1000")[["provincia", "canton", "tasa_egresos_x1000"]].to_string(index=False))

(DIR_EVIDENCIAS / "validacion_etl.txt").write_text("\n".join(registro), encoding="utf-8")
log(f"Cantones de población sin egresos (se asigna 0): {len(sin_egresos)}")
log(sin_egresos[["provincia", "canton", "poblacion"]].to_string(index=False))