
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
# Ruta de los datos
ruta = Path(__file__).resolve().parent.parent / "data" / "raw"

# Cargar los pedidos
pedidos = pd.read_csv(ruta / "olist_orders_dataset.csv")

print("\n========== EXPLORACIÓN INICIAL ==========")

print("\nPrimeros registros:")
print(pedidos.head())

print("\nDimensiones:")
print(f"Filas: {pedidos.shape[0]}")
print(f"Columnas: {pedidos.shape[1]}")

print("\nTipos de datos:")
print(pedidos.dtypes)

print("\nValores faltantes:")
print(pedidos.isnull().sum())

print("\nEstados de los pedidos:")
print(pedidos["order_status"].value_counts())

print("\n========== CALIDAD DE DATOS ==========")

# Valores faltantes
faltantes = pedidos.isnull().sum()

print("\nValores faltantes por columna:")
print(faltantes[faltantes > 0])

# Registros duplicados
print("\nPedidos duplicados:")
print(pedidos["order_id"].duplicated().sum())

# Conversión de fechas
columnas_fecha = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

for columna in columnas_fecha:
    pedidos[columna] = pd.to_datetime(
        pedidos[columna],
        errors="coerce"
    )

print("\nTipos de datos después de la conversión:")
print(pedidos.dtypes)

# Resumen de fechas
print("\nPeriodo de análisis:")
print("Primera compra:", pedidos["order_purchase_timestamp"].min())
print("Última compra:", pedidos["order_purchase_timestamp"].max())

print("\n========== DIAGNÓSTICO DE VALORES FALTANTES ==========")

# Crear indicadores de valores faltantes
pedidos["sin_aprobacion"] = pedidos["order_approved_at"].isna()
pedidos["sin_despacho"] = pedidos["order_delivered_carrier_date"].isna()
pedidos["sin_entrega"] = pedidos["order_delivered_customer_date"].isna()

# Analizar faltantes según estado
diagnostico = pedidos.groupby("order_status").agg(
    total_pedidos=("order_id", "count"),
    sin_aprobacion=("sin_aprobacion", "sum"),
    sin_despacho=("sin_despacho", "sum"),
    sin_entrega=("sin_entrega", "sum")
)

print(diagnostico)

# Comprobar fechas faltantes en pedidos entregados
entregados = pedidos[
    pedidos["order_status"] == "delivered"
]

print("\n========== PEDIDOS ENTREGADOS ==========")

print(
    "Entregados sin fecha de recepción:",
    entregados["order_delivered_customer_date"].isna().sum()
)

print(
    "Entregados sin fecha de despacho:",
    entregados["order_delivered_carrier_date"].isna().sum()
)

# Verificar duplicados
print("\n========== DUPLICADOS ==========")
print("ID de pedido duplicados:",
      pedidos["order_id"].duplicated().sum())

print("\n========== INVESTIGACIÓN DE ANOMALÍAS ==========")

# Seleccionar pedidos entregados con fechas faltantes
anomalías = pedidos[
    (pedidos["order_status"] == "delivered") &
    (
        pedidos["order_approved_at"].isna() |
        pedidos["order_delivered_carrier_date"].isna() |
        pedidos["order_delivered_customer_date"].isna()
    )
]

columnas_revision = [
    "order_id",
    "order_status",
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

print("\nPedidos entregados con fechas faltantes:")
print(anomalías[columnas_revision].to_string(index=False))

print("\nCantidad de registros:")
print(len(anomalías))


# Revisar fechas cronológicamente
print("\n========== VALIDACIÓN CRONOLÓGICA ==========")

entregados = pedidos[
    pedidos["order_status"] == "delivered"
].copy()

entregados["fecha_compra_aprobacion"] = (
    entregados["order_approved_at"] <
    entregados["order_purchase_timestamp"]
)

entregados["fecha_aprobacion_despacho"] = (
    entregados["order_delivered_carrier_date"] <
    entregados["order_approved_at"]
)

entregados["fecha_despacho_entrega"] = (
    entregados["order_delivered_customer_date"] <
    entregados["order_delivered_carrier_date"]
)

print("Aprobación anterior a compra:")
print(entregados["fecha_compra_aprobacion"].sum())

print("Despacho anterior a aprobación:")
print(entregados["fecha_aprobacion_despacho"].sum())

print("Entrega anterior a despacho:")
print(entregados["fecha_despacho_entrega"].sum())

print("\n========== VALIDACIÓN CRONOLÓGICA CORREGIDA ==========")

entregados = pedidos[
    pedidos["order_status"] == "delivered"
].copy()

# Definir las secuencias que queremos comprobar
secuencias = [
    (
        "Compra - Aprobación",
        "order_purchase_timestamp",
        "order_approved_at"
    ),
    (
        "Aprobación - Despacho",
        "order_approved_at",
        "order_delivered_carrier_date"
    ),
    (
        "Despacho - Entrega",
        "order_delivered_carrier_date",
        "order_delivered_customer_date"
    )
]

for nombre, fecha_inicio, fecha_fin in secuencias:

    # Solo comparar registros con ambas fechas disponibles
    validos = (
        entregados[fecha_inicio].notna() &
        entregados[fecha_fin].notna()
    )

    # Detectar fechas invertidas
    inconsistentes = (
        validos &
        (entregados[fecha_fin] < entregados[fecha_inicio])
    )

    print(f"\nSecuencia: {nombre}")
    print("Registros evaluables:", validos.sum())
    print("Fechas invertidas:", inconsistentes.sum())
    print("No evaluables:", (~validos).sum())

    # Mostrar ejemplos de inconsistencias
    if inconsistentes.sum() > 0:
        print("\nEjemplos encontrados:")

        print(
            entregados.loc[
                inconsistentes,
                ["order_id", fecha_inicio, fecha_fin]
            ].head(10).to_string(index=False)
        )

print("\n========== CONSTRUCCIÓN DE TABLA ANALÍTICA ==========")

# Copia de trabajo: no modificamos el CSV original
orders_clean = pedidos.copy()

# Indicadores de calidad
orders_clean["valid_purchase_delivery"] = (
    orders_clean["order_purchase_timestamp"].notna() &
    orders_clean["order_delivered_customer_date"].notna() &
    (
        orders_clean["order_delivered_customer_date"] >=
        orders_clean["order_purchase_timestamp"]
    )
)

orders_clean["valid_approval_dispatch"] = (
    orders_clean["order_approved_at"].notna() &
    orders_clean["order_delivered_carrier_date"].notna() &
    (
        orders_clean["order_delivered_carrier_date"] >=
        orders_clean["order_approved_at"]
    )
)

orders_clean["valid_dispatch_delivery"] = (
    orders_clean["order_delivered_carrier_date"].notna() &
    orders_clean["order_delivered_customer_date"].notna() &
    (
        orders_clean["order_delivered_customer_date"] >=
        orders_clean["order_delivered_carrier_date"]
    )
)

# Base para analizar tiempos de entrega total
delivery_analysis = orders_clean[
    (orders_clean["order_status"] == "delivered") &
    (orders_clean["valid_purchase_delivery"])
].copy()

# Calcular tiempo total de entrega en días
delivery_analysis["delivery_days"] = (
    delivery_analysis["order_delivered_customer_date"] -
    delivery_analysis["order_purchase_timestamp"]
).dt.total_seconds() / 86400

# Base para analizar el tramo de transporte
transport_analysis = orders_clean[
    (orders_clean["order_status"] == "delivered") &
    (orders_clean["valid_dispatch_delivery"])
].copy()

transport_analysis["transport_days"] = (
    transport_analysis["order_delivered_customer_date"] -
    transport_analysis["order_delivered_carrier_date"]
).dt.total_seconds() / 86400

# Guardar resultados
ruta_salida = Path(__file__).resolve().parent.parent / "data" / "processed"

ruta_salida.mkdir(parents=True, exist_ok=True)

(
    ruta_salida / "orders_clean.csv",
    index=False
)

delivery_analysis.to_csv(
    ruta_salida / "delivery_analysis.csv",
    index=False
)

transport_analysis.to_csv(
    ruta_salida / "transport_analysis.csv",
    index=False
)

# Resumen
print("\nPedidos entregados originales:", len(entregados))
print("Pedidos válidos para tiempo total:", len(delivery_analysis))
print("Pedidos válidos para transporte:", len(transport_analysis))

print("\nESTADÍSTICAS DE ENTREGA TOTAL")
print(delivery_analysis["delivery_days"].describe())
orders_clean.to_csv
print("\nESTADÍSTICAS DE TRANSPORTE")
print(transport_analysis["transport_days"].describe())

print("\nArchivos guardados en:", ruta_salida)
