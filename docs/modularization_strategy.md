# Modularization Strategy for Infranodal Codebase

## 1. Architecture Analysis

### 1.1 Current Structure
- **API Entrypoint (`main.py`)**: Monolithic FastAPI application that mixes configuration bootstrapping, domain logic (persona scoring, geospatial calculations), data-access helpers, and request handlers in a single ~1,000+ line file. This coupling makes the API hard to navigate and test.
- **Financial Model Backend (`backend/financial_model_api.py`, `backend/renewable_model.py`)**: Contains REST interface and core financial modeling logic. The modeling module mixes enumerations, dataclasses, simulation logic, cashflow calculations, and reporting helpers in a single file, creating unclear separation of concerns.
- **Data Acquisition Scripts (`fetch_network_data.py`, `fetch_fiber_data/`, `fetch_tnuos_data.py`, `import_projects.py`)**: Script-style modules directly orchestrate HTTP requests, processing, and Supabase persistence without reusable abstractions.
- **Shared Configuration**: Environment loading and Supabase credential handling duplicated across scripts and API modules.

### 1.2 Domain Boundaries
- **Platform Configuration & Infrastructure**: Environment management, Supabase connectivity, caching constants.
- **Geospatial Site Intelligence**: Persona weighting, scoring algorithms, geospatial models, and query orchestration exposed via the FastAPI app.
- **Financial Modeling**: Technology parameter definitions, price models, simulation engines, and API contract schemas.
- **Data Pipelines**: External dataset fetching, transformation, and loading into persistence layer.

These domains have limited separation; responsibilities are often interleaved, leading to high coupling and limited reuse.

## 2. Modularization Strategy

### 2.1 Proposed Top-Level Layout
```
infranodev2/
├── apps/
│   ├── api/                     # FastAPI presentation layer
│   │   ├── __init__.py
│   │   ├── bootstrap.py         # App creation & middleware
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── financial.py
│   │   │   └── infrastructure.py
│   │   └── dependencies.py      # Shared FastAPI dependencies (db, cache)
│   └── financial_api/           # If standalone API retained for modelling
├── core/
│   ├── config.py                # Settings, environment loading, constants
│   ├── logging.py
│   └── clients/
│       └── supabase.py          # Typed Supabase client wrapper
├── domain/
│   ├── financial/
│   │   ├── __init__.py
│   │   ├── models.py            # Dataclasses & enums (TechnologyParams, etc.)
│   │   ├── pricing.py           # MarketPrices & curve helpers
│   │   ├── simulation.py        # RenewableFinancialModel engine
│   │   ├── analytics.py         # Metric extraction, breakdowns
│   │   └── services.py          # Facade orchestrating scenarios for API
│   └── infrastructure/
│       ├── __init__.py
│       ├── personas.py          # Persona weights & scoring utilities
│       ├── geography.py         # Geospatial models & calculations
│       ├── datasets.py          # Dataset schemas & domain objects
│       └── services.py          # Query orchestration using repositories
├── data_pipeline/
│   ├── __init__.py
│   ├── clients.py               # HTTP/data source clients
│   ├── transformers.py
│   ├── loaders.py               # Supabase upload utilities
│   ├── tasks/
│   │   ├── network.py
│   │   ├── fiber.py
│   │   └── tnuos.py
│   └── cli.py                   # Typer/Click entry points for scripts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
└── docs/
    └── ...
```

### 2.2 Naming & Module Conventions
- **Package-level modules** named by bounded context (`domain.financial`, `domain.infrastructure`).
- **Files named by responsibility** (e.g., `simulation.py`, `services.py`) to signal purpose.
- **Explicit `__all__` exports** for public APIs; use `__init__.py` to re-export stable interfaces.

### 2.3 Dependency Guidelines
- `core` is foundational; it must not depend on `domain` or `apps`.
- `domain` may depend on `core` for configuration/logging but not on `apps` or `data_pipeline`.
- `apps` orchestrate dependencies and expose presentation logic; depend on `domain` and `core` only.
- `data_pipeline` depends on `core` for config and may reuse `domain` types where transformations align.
- Shared utilities (math helpers, enums) reside in `core.utils` or respective domain packages to avoid cross-import tangles.

### 2.4 Module Content Guidance
- **`apps.api`**: FastAPI app factory (`create_app()`), route definitions, request/response schemas, dependency injection wiring. No business logic or data access beyond orchestrating domain services.
- **`domain.financial`**: Core calculations (IRR, NPV, LCOE), technology abstractions, revenue breakdown, scenario orchestration. Keep pure functions and dataclasses for easier testing.
- **`domain.infrastructure`**: Persona scoring, site ranking algorithms, grid cell logic, domain-specific value objects.
- **`core`**: Environment management, logging configuration, caching TTL constants, typed clients for Supabase/HTTP.
- **`data_pipeline`**: ETL steps decomposed into Source -> Transform -> Load functions with dependency injection for clients and repositories.

## 3. Implementation Plan

### 3.1 Preparation
1. **Introduce packaging scaffolding**: Create `apps`, `core`, `domain`, and `data_pipeline` packages with `__init__.py` files.
2. **Add automated tests** (start with smoke/unit tests for financial calculations and key API endpoints) to guard refactoring.
3. **Document current public interfaces** (FastAPI routes, CLI entry points) to preserve contracts.

### 3.2 Refactor Order
1. **Core Configuration Extraction**
   - Move environment loading, constants, and Supabase client creation from `main.py` and scripts into `core.config` and `core.clients.supabase`.
   - Replace direct `os.getenv` usage with typed Pydantic `BaseSettings`.
2. **Financial Domain Isolation**
   - Split `backend/renewable_model.py` into `models.py` (enums/dataclasses), `simulation.py` (calculation engine), and `analytics.py` (cashflow/result summarization).
   - Wrap scenario orchestration currently in `financial_model_api.py` into `domain.financial.services`.
   - Update API modules to import from new packages.
3. **API Modularization**
   - Convert `main.py` into package `apps.api` with FastAPI factory and routers.
   - Extract route logic per domain (`financial`, `infrastructure`).
   - Move Pydantic schemas alongside routes or into `apps.api.schemas` if reused.
4. **Data Pipeline Modularization**
   - Refactor fetch scripts into `data_pipeline.tasks` using shared HTTP clients and transformers. Introduce CLI entry via Typer/Click.
5. **Shared Utilities**
   - Consolidate repeated helpers (e.g., persona weight constants, coordinate math) into domain-specific utility modules.
6. **Cleanup & Alignment**
   - Remove dead imports, update relative paths, and ensure `__all__` exposes stable API surfaces.

### 3.3 Handling Shared Code
- Promote reusable calculations to pure functions in `domain` modules.
- For cross-domain concerns (e.g., revenue breakdown used by multiple scenarios), create dedicated service classes or functions with explicit inputs/outputs.
- Introduce dependency injection via constructor arguments or FastAPI dependencies to avoid global state.

### 3.4 Testing Strategy
- **Baseline regression**: capture expected outputs from current API endpoints and financial model runs (golden files or contract tests).
- **Unit tests**: focus on pure functions in `domain` packages after extraction.
- **Integration tests**: run FastAPI app via `TestClient` hitting modularized routes.
- **Pipeline tests**: mock external APIs to validate ETL tasks.
- Run CI (pytest + lint) after each major refactor to catch regressions early.

## 4. Best Practices & Guidelines

### 4.1 Module Interfaces
- Expose **facade services** (e.g., `FinancialAnalysisService`) that return domain DTOs; keep implementation details private.
- Use **Pydantic models** for API contracts and separate **domain dataclasses** for internal logic to avoid tight coupling.

### 4.2 Avoiding Circular Dependencies
- Enforce `core -> domain -> apps` dependency direction via import linting (e.g., `flake8-import-order`, `pytest --import-mode=importlib`).
- Use dependency inversion where needed (e.g., repositories injected into services) rather than direct imports of concrete implementations.

### 4.3 Documentation Standards
- Maintain `docs/architecture.md` summarizing module responsibilities and dependency rules.
- Require docstrings for public functions and README per package describing entry points.
- Update onboarding docs to include module map and local development commands.

### 4.4 Future Module Additions
- Evaluate new features against existing bounded contexts; add packages under `domain` when introducing new business logic.
- Create new routers in `apps.api.routes` per feature to maintain clear API boundaries.
- For new data sources, add client/transformer/loader trio under `data_pipeline` to keep ETL consistent.
- Include tests and documentation updates in the definition of done for any new module.

---
Following this staged plan reduces file size, clarifies ownership, and aligns the repository with industry standards such as Clean Architecture, Domain-Driven Design boundaries, and 12-factor configuration management. The result is a codebase that is easier to onboard to, safer to refactor, and more amenable to automated testing.
