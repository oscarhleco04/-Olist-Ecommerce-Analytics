
import pandas as pd
from pathlib import Path

# ============================================================
# 1. CONFIGURACIÓN DE RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CARGA DE LOS DATASETS
# ============================================================

print("=" * 60)
print("ANÁLISIS COMERCIAL Y GEOGRÁFICO - OLIST")
print("=" * 60)

# Datos de pedidos con indicadores logísticos
orders = pd.read_csv(
    PROCESSED_DIR / "delivery_kpi.csv"
)

# Clientes
customers = pd.read_csv(
    RAW_DIR / "olist_customers_dataset.csv"
)

# Productos vendidos por pedido
order_items = pd.read_csv(
    RAW_DIR / "olist_order_items_dataset.csv"
)

# Información de productos
products = pd.read_csv(
    RAW_DIR / "olist_products_dataset.csv"
)

# Traducción de categorías
category_translation = pd.read_csv(
    RAW_DIR / "product_category_name_translation.csv"
)

# Vendedores
sellers = pd.read_csv(
    RAW_DIR / "olist_sellers_dataset.csv"
)

print("\nDatasets cargados correctamente:")
print(f"Pedidos: {len(orders):,}")
print(f"Clientes: {len(customers):,}")
print(f"Items vendidos: {len(order_items):,}")
print(f"Productos: {len(products):,}")
print(f"Vendedores: {len(sellers):,}")


# ============================================================
# 3. PREPARACIÓN DE LOS DATOS
# ============================================================

# Unir pedidos con información geográfica de clientes
orders_customers = orders.merge(
    customers[
        ["customer_id", "customer_state", "customer_city"]
    ],
    on="customer_id",
    how="left"
)

# Unir items con información de productos
items_products = order_items.merge(
    products[
        ["product_id", "product_category_name"]
    ],
    on="product_id",
    how="left"
)

# Incorporar nombres traducidos de categorías
items_products = items_products.merge(
    category_translation,
    on="product_category_name",
    how="left"
)

# Usar la categoría original cuando no exista traducción
items_products["categoria"] = (
    items_products["product_category_name_english"]
    .fillna(items_products["product_category_name"])
    .fillna("sin_categoria")
)

# Unir items con información de vendedores
seller_analysis = order_items.merge(
    sellers[
        ["seller_id", "seller_state", "seller_city"]
    ],
    on="seller_id",
    how="left"
)

# Incorporar información logística a los items
seller_analysis = seller_analysis.merge(
    orders[
        [
            "order_id",
            "cumplimiento",
            "delivery_days"
        ]
    ],
    on="order_id",
    how="inner"
)

print("\nPreparación de datos completada.")


# ============================================================
# 4. ANÁLISIS GEOGRÁFICO: ESTADO DEL CLIENTE
# ============================================================

print("\n" + "=" * 60)
print("4. ANÁLISIS GEOGRÁFICO POR ESTADO DEL CLIENTE")
print("=" * 60)

geographic_summary = (
    orders_customers
    .groupby("customer_state")
    .agg(
        total_pedidos=("order_id", "nunique"),
        pedidos_retrasados=(
            "cumplimiento",
            lambda x: (x == "Retrasado").sum()
        ),
        tiempo_promedio=("delivery_days", "mean"),
        tiempo_mediano=("delivery_days", "median")
    )
    .reset_index()
)

geographic_summary["porcentaje_retrasos"] = (
    geographic_summary["pedidos_retrasados"]
    / geographic_summary["total_pedidos"] * 100
)

# Ordenar por cantidad de pedidos
geographic_summary = geographic_summary.sort_values(
    "total_pedidos",
    ascending=False
)

print("\nResultados por estado del cliente:")
print(geographic_summary.round(2).to_string(index=False))

# Guardar resultados
geographic_summary.to_csv(
    PROCESSED_DIR / "geographic_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 5. ANÁLISIS COMERCIAL: CATEGORÍAS DE PRODUCTOS
# ============================================================

print("\n" + "=" * 60)
print("5. ANÁLISIS COMERCIAL POR CATEGORÍA")
print("=" * 60)

# Cada pedido se cuenta una sola vez por categoría.
# Un pedido con productos de distintas categorías aparecerá
# en cada una de las categorías correspondientes.

order_categories = (
    items_products[
        ["order_id", "categoria"]
    ]
    .drop_duplicates()
)

# Incorporar información logística
category_analysis = order_categories.merge(
    orders[
        [
            "order_id",
            "cumplimiento",
            "delivery_days"
        ]
    ],
    on="order_id",
    how="inner"
)

category_summary = (
    category_analysis
    .groupby("categoria")
    .agg(
        total_pedidos=("order_id", "nunique"),
        pedidos_retrasados=(
            "cumplimiento",
            lambda x: (x == "Retrasado").sum()
        ),
        tiempo_promedio=("delivery_days", "mean"),
        tiempo_mediano=("delivery_days", "median")
    )
    .reset_index()
)

category_summary["porcentaje_retrasos"] = (
    category_summary["pedidos_retrasados"]
    / category_summary["total_pedidos"] * 100
)

# Ordenar por volumen de pedidos
category_summary = category_summary.sort_values(
    "total_pedidos",
    ascending=False
)

print("\nTop 10 categorías por volumen de pedidos:")
print(
    category_summary.head(10)
    .round(2)
    .to_string(index=False)
)

print("\nTop 10 categorías por porcentaje de retrasos:")
print(
    category_summary.sort_values(
        "porcentaje_retrasos",
        ascending=False
    )
    .head(10)
    .round(2)
    .to_string(index=False)
)

# Guardar resultados
category_summary.to_csv(
    PROCESSED_DIR / "category_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 6. ANÁLISIS DE VENDEDORES POR ESTADO
# ============================================================

print("\n" + "=" * 60)
print("6. ANÁLISIS DE VENDEDORES POR ESTADO")
print("=" * 60)

# Resumen general:
# Cada pedido se cuenta una sola vez dentro de cada estado.
seller_summary = (
    seller_analysis
    .groupby("seller_state")
    .agg(
        pedidos_asociados=("order_id", "nunique"),
        vendedores=("seller_id", "nunique"),
        tiempo_promedio=("delivery_days", "mean")
    )
    .reset_index()
)

# Contar pedidos retrasados únicos por estado del vendedor.
# Esto evita contar varias veces el mismo pedido cuando
# contiene múltiples items del mismo estado.
retrasos_vendedor = (
    seller_analysis[
        seller_analysis["cumplimiento"] == "Retrasado"
    ]
    .groupby("seller_state")["order_id"]
    .nunique()
    .reset_index(name="pedidos_retrasados")
)

# Incorporar los retrasos al resumen general
seller_summary = seller_summary.merge(
    retrasos_vendedor,
    on="seller_state",
    how="left"
)

seller_summary["pedidos_retrasados"] = (
    seller_summary["pedidos_retrasados"].fillna(0)
)

# Calcular porcentaje de pedidos retrasados asociados
seller_summary["porcentaje_retrasos"] = (
    seller_summary["pedidos_retrasados"]
    / seller_summary["pedidos_asociados"] * 100
)

# Ordenar por volumen
seller_summary = seller_summary.sort_values(
    "pedidos_asociados",
    ascending=False
)

print("\nResultados corregidos por estado del vendedor:")
print(seller_summary.round(2).to_string(index=False))

# Guardar resultados
seller_summary.to_csv(
    PROCESSED_DIR / "seller_analysis.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 7. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 60)
print("ARCHIVOS GENERADOS")
print("=" * 60)

print("\nSe generaron los siguientes archivos:")

print(
    PROCESSED_DIR / "geographic_analysis.csv"
)

print(
    PROCESSED_DIR / "category_analysis.csv"
)

print(
    PROCESSED_DIR / "seller_analysis.csv"
)

print("\nAnálisis comercial y geográfico finalizado correctamente.")
orders = pd.read_csv(
    PROCESSED_DIR / "delivery_kpi.csv"
)