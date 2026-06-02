import pandas as pd
import zipfile
from sqlalchemy import create_engine, text

# 1. KONFIGURASI DATABASE
# Sesuaikan dengan kredensial di docker-compose kamu
DB_URL = 'postgresql://admin:********@127.0.0.1:5432/olist_dw'
engine = create_engine(DB_URL)

CSV_COLUMNS = {
    'orders': [
        'order_id', 'customer_id', 'order_purchase_timestamp',
        'order_estimated_delivery_date', 'order_delivered_customer_date'
    ],
    'items': [
        'order_id', 'product_id', 'seller_id', 'price', 'freight_value'
    ],
    'payments': ['order_id', 'payment_value'],
    'reviews': [
        'order_id', 'review_id', 'review_score',
        'review_comment_title', 'review_comment_message'
    ],
    'products': ['product_id', 'product_category_name', 'product_weight_g'],
    'customers': [
        'customer_id', 'customer_unique_id', 'customer_city',
        'customer_state', 'customer_zip_code_prefix'
    ],
    'sellers': ['seller_id', 'seller_city', 'seller_state'],
    'translation': ['product_category_name', 'product_category_name_english']
}


def extract_data(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        print('--- Step 1: Extracting & Reading Data ---')
        orders = pd.read_csv(z.open('olist_orders_dataset.csv'), usecols=CSV_COLUMNS['orders'])
        items = pd.read_csv(z.open('olist_order_items_dataset.csv'), usecols=CSV_COLUMNS['items'])
        payments = pd.read_csv(z.open('olist_order_payments_dataset.csv'), usecols=CSV_COLUMNS['payments'])
        reviews = pd.read_csv(z.open('olist_order_reviews_dataset.csv'), usecols=CSV_COLUMNS['reviews'])
        products = pd.read_csv(z.open('olist_products_dataset.csv'), usecols=CSV_COLUMNS['products'])
        customers = pd.read_csv(z.open('olist_customers_dataset.csv'), usecols=CSV_COLUMNS['customers'])
        sellers = pd.read_csv(z.open('olist_sellers_dataset.csv'), usecols=CSV_COLUMNS['sellers'])
        translation = pd.read_csv(z.open('product_category_name_translation.csv'), usecols=CSV_COLUMNS['translation'])

    return {
        'orders': orders,
        'items': items,
        'payments': payments,
        'reviews': reviews,
        'products': products,
        'customers': customers,
        'sellers': sellers,
        'translation': translation
    }


def transform_dimensions(customers, products, translation, sellers, reviews):
    print('--- Step 2: Transforming Dimensions ---')

    dim_customer = customers[
        ['customer_unique_id', 'customer_city', 'customer_state', 'customer_zip_code_prefix']
    ].rename(columns={
        'customer_unique_id': 'customer_key',
        'customer_city': 'city',
        'customer_state': 'state',
        'customer_zip_code_prefix': 'zip_code'
    }).drop_duplicates(subset=['customer_key'])

    dim_product = (
        products
        .merge(translation, on='product_category_name', how='left')
        [['product_id', 'product_category_name_english', 'product_weight_g']]
        .rename(columns={
            'product_id': 'product_key',
            'product_category_name_english': 'category_name_en',
            'product_weight_g': 'weight_g'
        })
    )

    dim_seller = sellers.rename(columns={
        'seller_id': 'seller_key',
        'seller_city': 'city',
        'seller_state': 'state'
    })

    dim_review = (
        reviews
        [['review_id', 'review_comment_title', 'review_comment_message']]
        .rename(columns={'review_id': 'review_key'})
        .drop_duplicates(subset=['review_key'])
    )

    return dim_date, dim_customer, dim_product, dim_seller, dim_review


def transform_fact(orders, items, customers, payments, reviews):
    print('--- Step 3: Transforming Fact Table ---')

    orders = orders.copy()
    orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
    orders['order_purchase_date'] = orders['order_purchase_timestamp'].dt.normalize()
    orders['order_purchase_time'] = orders['order_purchase_timestamp'].dt.strftime('%H:%M:%S')
    orders['order_purchase_hour'] = orders['order_purchase_timestamp'].dt.hour
    orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'])
    orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'])

    fact = items.merge(orders, on='order_id')
    fact = fact.merge(customers[['customer_id', 'customer_unique_id']], on='customer_id', how='left')

    pay_agg = payments.groupby('order_id', as_index=False)['payment_value'].sum()
    fact = fact.merge(pay_agg, on='order_id', how='left')

    rev_agg = (
        reviews
        .groupby('order_id', as_index=False)
        .agg({'review_id': 'first', 'review_score': 'mean'})
    )
    fact = fact.merge(rev_agg, on='order_id', how='left')

    fact['delivery_days'] = (fact['order_delivered_customer_date'] - fact['order_purchase_timestamp']).dt.days
    fact['is_late'] = fact['order_delivered_customer_date'] > fact['order_estimated_delivery_date']

    fact_sales = (
        fact[
            [
                'order_id', 'customer_unique_id', 'product_id', 'seller_id', 'review_id',
                'order_purchase_date', 'order_purchase_timestamp',
                'order_purchase_time', 'order_purchase_hour',
                'price', 'freight_value', 'payment_value',
                'review_score', 'delivery_days', 'is_late'
            ]
        ]
        .rename(columns={
            'customer_unique_id': 'customer_key',
            'product_id': 'product_key',
            'seller_id': 'seller_key',
            'review_id': 'review_key',
            'order_purchase_date': 'date_key',
            'order_purchase_timestamp': 'order_timestamp'
        })
    )

    unique_dates = fact_sales['date_key'].dt.normalize().drop_duplicates().sort_values()
    dim_date = pd.DataFrame({'date_key': unique_dates})
    dim_date['day'] = dim_date['date_key'].dt.day
    dim_date['month'] = dim_date['date_key'].dt.month
    dim_date['year'] = dim_date['date_key'].dt.year
    dim_date['quarter'] = dim_date['date_key'].dt.quarter
    dim_date['day_name'] = dim_date['date_key'].dt.day_name()
    dim_date['month_name'] = dim_date['date_key'].dt.month_name()

    return dim_date, fact_sales


def load_tables(tables):
    print('--- Step 4: Loading to PostgreSQL ---')
    with engine.begin() as connection:
        for table_name, df in tables:
            df.to_sql(
                table_name,
                connection,
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )


def run_full_etl(zip_path):
    try:
        data = extract_data(zip_path)

        dim_customer = data['customers'][
            ['customer_unique_id', 'customer_city', 'customer_state', 'customer_zip_code_prefix']
        ].rename(columns={
            'customer_unique_id': 'customer_key',
            'customer_city': 'city',
            'customer_state': 'state',
            'customer_zip_code_prefix': 'zip_code'
        }).drop_duplicates(subset=['customer_key'])

        dim_product = (
            data['products']
            .merge(data['translation'], on='product_category_name', how='left')
            [['product_id', 'product_category_name_english', 'product_weight_g']]
            .rename(columns={
                'product_id': 'product_key',
                'product_category_name_english': 'category_name_en',
                'product_weight_g': 'weight_g'
            })
        )

        dim_seller = data['sellers'].rename(columns={
            'seller_id': 'seller_key',
            'seller_city': 'city',
            'seller_state': 'state'
        })

        dim_review = (
            data['reviews']
            [['review_id', 'review_comment_title', 'review_comment_message']]
            .rename(columns={'review_id': 'review_key'})
            .drop_duplicates(subset=['review_key'])
        )

        dim_date, fact_sales = transform_fact(
            data['orders'],
            data['items'],
            data['customers'],
            data['payments'],
            data['reviews']
        )

        load_tables([
            ('DimDate', dim_date),
            ('DimCustomer', dim_customer),
            ('DimProduct', dim_product),
            ('DimSeller', dim_seller),
            ('DimReview', dim_review),
            ('FactSales', fact_sales)
        ])

        print('\nETL PROSES BERHASIL!')
        print(f"Data Warehouse '{DB_URL}' sekarang sudah terisi.")

    except Exception as e:
        print(f'TERJADI ERROR: {e}')


if __name__ == '__main__':
    run_full_etl('olist.zip')
