
from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# 1. CONFIGURACIÓN DE RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 2. CARGA DE DATOS
# ============================================================

print("\n" + "=" * 65)
print("ETAPA 04: ANALISIS TEMPORAL Y COMERCIAL - OLIST")
print("=" * 65)

orders = pd.read_csv(
    RAW_DIR / "olist_orders_dataset.csv"
)

items = pd.read_csv(
    RAW_DIR / "olist_order_items_dataset.csv"
)

payments = pd.read_csv(
    RAW_DIR / "olist_order_payments_dataset.csv"
)

customers = pd.read_csv(
    RAW_DIR / "olist_customers_dataset.csv"
)

delivery = pd.read_csv(
    PROCESSED_DIR / "delivery_kpi.csv"
)

# Convertir fechas
orders["order_purchase_timestamp"] = pd.to_datetime(
    orders["order_purchase_timestamp"],
    errors="coerce"
)

delivery["order_purchase_timestamp"] = pd.to_datetime(
    delivery["order_purchase_timestamp"],
    errors="coerce"
)

print("\nDATOS CARGADOS")
print("-" * 65)
print(f"Pedidos: {len(orders):,}")
print(f"Articulos: {len(items):,}")
print(f"Registros de pago: {len(payments):,}")
print(f"Clientes: {len(customers):,}")
print(f"Pedidos con KPI logistico: {len(delivery):,}")

# ============================================================
# 3. AGREGACIÓN DE ARTÍCULOS POR PEDIDO
# ============================================================

# Cada pedido puede contener varios artículos.
# Primero calculamos sus importes a nivel de pedido.

items_by_order = (
    items.groupby("order_id")
    .agg(
        cantidad_articulos=("order_item_id", "count"),
        venta_productos=("price", "sum"),
        costo_envio=("freight_value", "sum")
    )
    .reset_index()
)

items_by_order["valor_pedido"] = (
    items_by_order["venta_productos"]
    + items_by_order["costo_envio"]
)

print("\nAGREGACION DE ARTICULOS")
print("-" * 65)
print(f"Pedidos con articulos: {len(items_by_order):,}")
print(
    "Valor total de productos: R$ "
    f"{items_by_order['venta_productos'].sum():,.2f}"
)
print(
    "Valor total de envios: R$ "
    f"{items_by_order['costo_envio'].sum():,.2f}"
)

# ============================================================
# 4. AGREGACIÓN DE PAGOS POR PEDIDO
# ============================================================

# Un pedido puede tener varios registros de pago.
# Se suman antes de unirlos con los artículos.

payments_by_order = (
    payments.groupby("order_id")
    .agg(
        pago_total=("payment_value", "sum"),
        numero_registros_pago=("payment_value", "count")
    )
    .reset_index()
)

# ============================================================
# 5. CONSTRUCCIÓN DE LA BASE A NIVEL DE PEDIDO
# ============================================================

# Partimos de todos los pedidos.
# Así conservamos los pedidos cancelados y otros estados
# para analizar la evolución de la demanda.

orders_analysis = orders.merge(
    items_by_order,
    on="order_id",
    how="left"
)

orders_analysis = orders_analysis.merge(
    payments_by_order,
    on="order_id",
    how="left"
)

orders_analysis = orders_analysis.merge(
    customers[["customer_id", "customer_unique_id"]],
    on="customer_id",
    how="left"
)

# Crear variable temporal mensual
orders_analysis["mes"] = (
    orders_analysis["order_purchase_timestamp"]
    .dt.to_period("M")
    .astype("string")
)

# Identificar pedidos entregados
orders_analysis["es_entregado"] = (
    orders_analysis["order_status"] == "delivered"
)

# Para el análisis de ventas realizadas,
# consideramos únicamente pedidos entregados.
orders_analysis["venta_entregada"] = np.where(
    orders_analysis["es_entregado"],
    orders_analysis["valor_pedido"],
    np.nan
)

# ============================================================
# 6. EVOLUCIÓN MENSUAL DE PEDIDOS Y VENTAS
# ============================================================

monthly_commercial = (
    orders_analysis.groupby("mes", dropna=True)
    .agg(
        total_pedidos=("order_id", "nunique"),
        pedidos_entregados=("es_entregado", "sum"),
        ventas_productos=(
            "venta_productos",
            lambda x: x[orders_analysis.loc[x.index, "es_entregado"]].sum()
        ),
        ingresos_envio=(
            "costo_envio",
            lambda x: x[orders_analysis.loc[x.index, "es_entregado"]].sum()
        ),
        ventas_totales=(
            "venta_entregada",
            "sum"
        ),
        clientes_unicos=("customer_unique_id", "nunique")
    )
    .reset_index()
)

monthly_commercial["ticket_promedio"] = (
    monthly_commercial["ventas_totales"]
    / monthly_commercial["pedidos_entregados"].replace(0, np.nan)
)

monthly_commercial["crecimiento_pedidos_pct"] = (
    monthly_commercial["total_pedidos"].pct_change() * 100
)

monthly_commercial["crecimiento_ventas_pct"] = (
    monthly_commercial["ventas_totales"].pct_change() * 100
)

monthly_commercial["porcentaje_entregados"] = (
    monthly_commercial["pedidos_entregados"]
    / monthly_commercial["total_pedidos"].replace(0, np.nan)
    * 100
)

print("\nEVOLUCION MENSUAL COMERCIAL")
print("-" * 65)
print(monthly_commercial.tail(15).to_string(index=False))

# ============================================================
# 7. ANÁLISIS DE CUMPLIMIENTO LOGÍSTICO POR MES
# ============================================================

# delivery_kpi contiene pedidos entregados y su clasificación
# respecto a la fecha estimada.

delivery["mes"] = (
    delivery["order_purchase_timestamp"]
    .dt.to_period("M")
    .astype("string")
)

monthly_logistics = (
    delivery.groupby("mes", dropna=True)
    .agg(
        pedidos_evaluados=("order_id", "nunique"),
        pedidos_adelantados=(
            "cumplimiento",
            lambda x: (x == "Adelantado").sum()
        ),
        pedidos_a_tiempo=(
            "cumplimiento",
            lambda x: (x == "A tiempo").sum()
        ),
        pedidos_retrasados=(
            "cumplimiento",
            lambda x: (x == "Retrasado").sum()
        ),
        retraso_promedio=(
            "dias_diferencia",
            lambda x: x[x > 0].mean()
        )
    )
    .reset_index()
)

monthly_logistics["porcentaje_retrasados"] = (
    monthly_logistics["pedidos_retrasados"]
    / monthly_logistics["pedidos_evaluados"].replace(0, np.nan)
    * 100
)

monthly_logistics["porcentaje_adelantados"] = (
    monthly_logistics["pedidos_adelantados"]
    / monthly_logistics["pedidos_evaluados"].replace(0, np.nan)
    * 100
)

print("\nEVOLUCION MENSUAL LOGISTICA")
print("-" * 65)
print(monthly_logistics.tail(15).to_string(index=False))

# ============================================================
# 8. ANÁLISIS DE MEDIOS DE PAGO
# ============================================================

# Vinculamos pagos con pedidos entregados.
# La base de pagos se mantiene a nivel de registro de pago.

delivered_ids = orders_analysis.loc[
    orders_analysis["es_entregado"],
    ["order_id", "mes"]
].drop_duplicates()

payments_delivered = payments.merge(
    delivered_ids,
    on="order_id",
    how="inner"
)

payment_method_analysis = (
    payments_delivered.groupby("payment_type")
    .agg(
        numero_registros=("payment_value", "count"),
        valor_total=("payment_value", "sum"),
        valor_promedio=("payment_value", "mean")
    )
    .reset_index()
    .sort_values("valor_total", ascending=False)
)

payment_method_analysis["participacion_valor_pct"] = (
    payment_method_analysis["valor_total"]
    / payment_method_analysis["valor_total"].sum()
    * 100
)

print("\nANALISIS DE MEDIOS DE PAGO")
print("-" * 65)
print(payment_method_analysis.to_string(index=False))

# ============================================================
# 9. ANÁLISIS DE CLIENTES RECURRENTES
# ============================================================

# customer_unique_id permite reconocer al mismo cliente
# aunque tenga diferentes customer_id.

customer_orders = (
    orders_analysis.dropna(subset=["customer_unique_id"])
    .groupby("customer_unique_id")
    .agg(
        total_pedidos=("order_id", "nunique"),
        pedidos_entregados=("es_entregado", "sum")
    )
    .reset_index()
)

customer_orders["tipo_cliente"] = np.where(
    customer_orders["pedidos_entregados"] > 1,
    "Recurrente",
    "Una sola compra entregada"
)

customer_repeat_analysis = (
    customer_orders.groupby("tipo_cliente")
    .agg(
        cantidad_clientes=("customer_unique_id", "count"),
        pedidos_entregados=("pedidos_entregados", "sum")
    )
    .reset_index()
)

customer_repeat_analysis["participacion_clientes_pct"] = (
    customer_repeat_analysis["cantidad_clientes"]
    / customer_repeat_analysis["cantidad_clientes"].sum()
    * 100
)

print("\nANALISIS DE CLIENTES")
print("-" * 65)
print(customer_repeat_analysis.to_string(index=False))

# ============================================================
# 10. CONCILIACIÓN DE VENTAS Y PAGOS
# ============================================================

# Comparamos el valor de artículos + envío con el total pagado.
# Las diferencias pueden deberse a descuentos, vouchers,
# ajustes u otros componentes de la operación.

financial_reconciliation = orders_analysis.loc[
    orders_analysis["es_entregado"],
    [
        "order_id",
        "valor_pedido",
        "pago_total"
    ]
].copy()

financial_reconciliation["diferencia_pago_venta"] = (
    financial_reconciliation["pago_total"]
    - financial_reconciliation["valor_pedido"]
)

print("\nCONCILIACION FINANCIERA")
print("-" * 65)
print(
    "Pedidos entregados con valor de artículos y envío:",
    financial_reconciliation["valor_pedido"].notna().sum()
)
print(
    "Pedidos entregados con información de pago:",
    financial_reconciliation["pago_total"].notna().sum()
)
print(
    "Diferencia total pagos - artículos y envío: R$ "
    f"{financial_reconciliation['diferencia_pago_venta'].sum():,.2f}"
)
print(
    "Diferencia promedio por pedido: R$ "
    f"{financial_reconciliation['diferencia_pago_venta'].mean():,.2f}"
)

# ============================================================
# 11. EXPORTACIÓN DE RESULTADOS
# ============================================================

monthly_commercial.to_csv(
    PROCESSED_DIR / "monthly_commercial_analysis.csv",
    index=False
)

monthly_logistics.to_csv(
    PROCESSED_DIR / "monthly_logistics_analysis.csv",
    index=False
)

payment_method_analysis.to_csv(
    PROCESSED_DIR / "payment_method_analysis.csv",
    index=False
)

customer_repeat_analysis.to_csv(
    PROCESSED_DIR / "customer_repeat_analysis.csv",
    index=False
)

orders_analysis.to_csv(
    PROCESSED_DIR / "order_level_financial.csv",
    index=False
)

financial_reconciliation.to_csv(
    PROCESSED_DIR / "financial_reconciliation.csv",
    index=False
)

print("\n" + "=" * 65)
print("ANALISIS TEMPORAL Y COMERCIAL FINALIZADO")
print("=" * 65)

print("\nARCHIVOS GENERADOS:")
print("- monthly_commercial_analysis.csv")
print("- monthly_logistics_analysis.csv")
print("- payment_method_analysis.csv")
print("- customer_repeat_analysis.csv")
print("- order_level_financial.csv")
print("- financial_reconciliation.csv")
