# Aquarium Fish Shop Microservices

Greenfield aquarium e-commerce platform as decoupled Python/FastAPI microservices, each owning its data, communicating via synchronous HTTP and Redis Streams events, fronted by a FastAPI API Gateway, with a dedicated React storefront frontend.

Specializes in freshwater and saltwater fish, corals, invertebrates, aquatic plants, and aquarium equipment & supplies. Features live animal guarantees (DOA protection), species compatibility data, and climate-aware shipping support.

## Architecture
- **Stack:** Python + FastAPI (async), React storefront, Redis Streams, Docker Compose
- **Database:** one database per service; SQLite for local development, PostgreSQL for production
- **Services:** users, catalog, inventory, orders, payments, gateway, storefront
- **Events:** Redis Streams with consumer groups, transactional outbox, idempotent handlers, dead-letter stream

## Aquarium domain features
- Livestock products with species, scientific name, water type, care level, temperature/pH ranges, temperament
- WYSIWYG (unique specimen) flag for corals and rare fish
- DOA (Dead on Arrival) claim handling with evidence
- Stock reservations with livestock tracking

## Planning
Detailed design decisions, service boundaries, data flow, failure modes, security requirements, and the ordered implementation task list are in `PLAN.md`.

## Repository layout
```
C:\Development\Microservices\
├── PLAN.md            # Full architecture & implementation plan
├── README.md          # this file
├── docs/              # 17 documentation files (BRD, PRD, SRS, HLD, ADRs, etc.)
├── docker-compose.yml # Redis + 6 service containers + storefront
├── .env.example       # environment variable template
├── gateway/           # FastAPI API gateway
├── users/             # users service
├── catalog/           # catalog service (aquarium products)
├── inventory/         # inventory service (livestock tracking, DOA)
├── orders/            # orders service (state machine, DOA claims)
├── payments/          # payments service (Stripe sandbox)
├── storefront/        # dedicated React storefront UI
├── shared/            # Redis helpers, event schemas, outbox relay
└── tests/             # 49 pytest test cases
```

## Status
Planning and core services implemented. 49 tests passing. Storefront (Stage 8) and production wiring (Stages 9-12) remaining. No application code changes beyond services 1-7 yet.