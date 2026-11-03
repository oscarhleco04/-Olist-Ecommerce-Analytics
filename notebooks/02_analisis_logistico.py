
import pandas as pd
import numpy as np

# =====================================================
# 1. CARGA DE DATOS
# =====================================================

print("\n========== CARGA DE DATOS ==========")

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ruta = BASE_DIR / "data" / "processed" / "delivery_analysis.csv"

delivery = pd.read_csv(ruta)
# Convertir columnas de fechas a formato datetime
columnas_fecha = [
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

for columna in columnas_fecha:
    delivery[columna] = pd.to_datetime(
        delivery[columna],
        errors="coerce"
    )

print("Registros cargados:", len(delivery))


# =====================================================
# 2. CÁLCULO DEL CUMPLIMIENTO DE ENTREGAS
# =====================================================

print("\n========== CUMPLIMIENTO DE ENTREGAS ==========")

# Normalizar las fechas para comparar únicamente días
delivery["fecha_real"] = (
    delivery["order_delivered_customer_date"].dt.normalize()
)

delivery["fecha_estimada"] = (
    delivery["order_estimated_delivery_date"].dt.normalize()
)

# Diferencia entre fecha real y estimada
delivery["dias_diferencia"] = (
    delivery["fecha_real"] - delivery["fecha_estimada"]
).dt.total_seconds() / 86400

# Clasificar cumplimiento
delivery["cumplimiento"] = "A tiempo"

delivery.loc[
    delivery["dias_diferencia"] > 0,
    "cumplimiento"
] = "Retrasado"

delivery.loc[
    delivery["dias_diferencia"] < 0,
    "cumplimiento"
] = "Adelantado"

# Frecuencia de cada categoría
conteo_cumplimiento = delivery["cumplimiento"].value_counts()

print(conteo_cumplimiento)

# Porcentajes
porcentajes = (
    delivery["cumplimiento"]
    .value_counts(normalize=True) * 100
)

print("\nPorcentajes:")
print(porcentajes.round(2))


# =====================================================
# 3. ANÁLISIS DE LOS DÍAS DE RETRASO
# =====================================================

print("\n========== DÍAS DE RETRASO ==========")

retrasados = delivery[
    delivery["cumplimiento"] == "Retrasado"
]

print(
    retrasados["dias_diferencia"].describe()
)


# =====================================================
# 4. RESUMEN DE TIEMPOS DE ENTREGA
# =====================================================

print("\n========== RESUMEN DE ENTREGA ==========")

resumen_entrega = (
    delivery.groupby("cumplimiento")["delivery_days"]
    .agg(["count", "mean", "median"])
)

print(resumen_entrega)


# =====================================================
# 5. DETECCIÓN DE VALORES ATÍPICOS
# =====================================================

print("\n========== DETECCIÓN DE VALORES ATÍPICOS ==========")

# Cuartiles
Q1 = delivery["delivery_days"].quantile(0.25)
Q3 = delivery["delivery_days"].quantile(0.75)

# Rango intercuartílico
IQR = Q3 - Q1

# Límites para identificar valores atípicos
lower = Q1 - (1.5 * IQR)
upper = Q3 + (1.5 * IQR)

print("Q1:", round(Q1, 2))
print("Q3:", round(Q3, 2))
print("IQR:", round(IQR, 2))
print("Límite inferior:", round(lower, 2))
print("Límite superior:", round(upper, 2))

# Identificar pedidos atípicos
atipicos = delivery[
    (delivery["delivery_days"] < lower) |
    (delivery["delivery_days"] > upper)
]

print("Pedidos atípicos:", len(atipicos))

porcentaje_atipicos = (
    len(atipicos) / len(delivery)
) * 100

print(
    "Porcentaje de pedidos atípicos:",
    round(porcentaje_atipicos, 2),
    "%"
)


# =====================================================
# 6. IDENTIFICACIÓN DE LOS MAYORES TIEMPOS DE ENTREGA
# =====================================================

print("\n========== MAYORES TIEMPOS DE ENTREGA ==========")

columnas_resultado = [
    "order_id",
    "delivery_days",
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

mayores_entregas = delivery.nlargest(
    10,
    "delivery_days"
)[columnas_resultado]

print(mayores_entregas.to_string(index=False))


# =====================================================
# 7. INVESTIGACIÓN DE ENTREGAS DEL 19/09/2017
# =====================================================

print("\n========== ENTREGAS DEL 19/09/2017 ==========")

fecha_critica = delivery[
    delivery["order_delivered_customer_date"].dt.date
    == pd.Timestamp("2017-09-19").date()
]

print("Cantidad de pedidos:", len(fecha_critica))

print("\nFechas de compra:")
print(
    fecha_critica["order_purchase_timestamp"].describe()
)

print("\nFechas estimadas:")
print(
    fecha_critica["order_estimated_delivery_date"].describe()
)


# =====================================================
# 8. COMPARACIÓN DE PEDIDOS ATÍPICOS Y NO ATÍPICOS
# =====================================================

print("\n========== COMPARACIÓN DE ATÍPICOS ==========")

delivery["es_atipico"] = (
    (delivery["delivery_days"] < lower) |
    (delivery["delivery_days"] > upper)
)

comparacion = (
    delivery.groupby("es_atipico")["delivery_days"]
    .agg(["count", "mean", "median", "max"])
)

print(comparacion)


# =====================================================
# 9. EXPORTACIÓN DE RESULTADOS
# =====================================================

print("\n========== EXPORTACIÓN ==========")


PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

delivery.to_csv(
    PROCESSED_DIR / "delivery_kpi.csv",
    index=False,
    encoding="utf-8-sig"
)



atipicos.to_csv(
    PROCESSED_DIR / "delivery_outliers.csv",
    index=False,
    encoding="utf-8-sig"
)


print("Archivos guardados correctamente:")
print("- data/processed/delivery_kpi.csv")
print("- data/processed/delivery_outliers.csv")

print("\n========== ANÁLISIS FINALIZADO ==========")
