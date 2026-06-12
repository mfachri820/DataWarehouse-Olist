<img width="1167" height="816" alt="Screenshot 2026-06-12 161647" src="https://github.com/user-attachments/assets/8e3d2082-ca25-4d4f-8930-a29eedd5c198" />

# Data Warehouse Project - Olist

A data warehouse implementation using PostgreSQL with Star Schema design for Olist e-commerce data analysis.

## Overview

This project implements an ETL (Extract, Transform, Load) pipeline that processes Olist e-commerce data and loads it into a PostgreSQL data warehouse with a Star Schema structure.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   olist.zip     │────▶│    ingest.py    │────▶│  PostgreSQL     │
│ (Raw Data)      │     │   (ETL Script)  │     │  (Star Schema)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Star Schema Design

### Fact Table
- **FactSales** - Central fact table containing sales transactions

### Dimension Tables
- **DimCustomer** - Customer information (city, state, zip code)
- **DimProduct** - Product details (category, weight)
- **DimSeller** - Seller information (city, state)
- **DimDate** - Date dimension for time-based analysis
- **DimReview** - Review data (score, comments)

## Prerequisites

- Docker & Docker Compose
- Python 3.x
- Node.js (for Prisma Studio)

## Setup

### 1. Configure Environment Variables

Copy the example environment file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your preferred password:
```
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://admin:your_secure_password@localhost:5432/olist_dw
```

### 2. Start PostgreSQL Container

```bash
docker compose up -d
```

### 3. Run ETL Pipeline

```bash
pip install pandas sqlalchemy psycopg2-binary
python ingest.py
```

### 4. Access Prisma Studio (Optional)

```bash
npx prisma studio
```

## Project Structure

```
.
├── .env                  # Environment variables (not tracked)
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── docker-compose.yml      # PostgreSQL container setup
├── ingest.py             # ETL pipeline script
├── olist.zip             # Olist dataset
├── package.json          # Node.js dependencies
├── prisma/
│   ├── schema.prisma     # Database schema
│   └── migrations/       # Database migrations
└── prisma.config.ts      # Prisma configuration
```

## Data Sources

The `olist.zip` file contains the following datasets:
- `olist_orders_dataset.csv` - Order information
- `olist_order_items_dataset.csv` - Order items and pricing
- `olist_order_payments_dataset.csv` - Payment data
- `olist_order_reviews_dataset.csv` - Customer reviews
- `olist_products_dataset.csv` - Product catalog
- `olist_customers_dataset.csv` - Customer data
- `olist_sellers_dataset.csv` - Seller information
- `product_category_name_translation.csv` - Category translations

## ETL Process

1. **Extract** - Read CSV files from the zip archive
2. **Transform** - Clean and transform data into star schema format
3. **Load** - Insert transformed data into PostgreSQL tables

## Database Connection

- **Host**: localhost
- **Port**: 5432
- **Database**: olist_dw
- **User**: admin

## Security Note

Never commit `.env` file to version control. It contains sensitive credentials.

## License

ISC
