# SYSTEM DESIGN

## System Layout
The system follows Clean Architecture principles as defined in `ADR-004`. The layout is designed to separate business logic from infrastructure concerns.
Each module follows the `domain/ports/adapters/use_cases/api` structure:
- **domain/**: Contains pure business logic and models. No external dependencies.
- **ports/**: Defines the interfaces (protocols) for infrastructure interactions.
- **adapters/**: Implementations of the ports (e.g., SQLite, Redis, LocalAI).
- **use_cases/**: Orchestrates the domain logic with the ports.
- **api/**: The presentation layer, exposing routes or CLI commands.

## Data Stores
The system utilizes multiple data stores based on the specific module requirements:
- **SQLite**: Used by the Second Brain for persisting knowledge, verdicts, and incidents locally.
- **Redis**: Used as an upgrade adapter for higher performance and pub/sub event bus mechanism.

## Contracts
Contracts between phases are defined by the port interfaces. For example, `KnowledgeRepository` and `VLMProvider` act as the source of truth for the adapter implementations.

## Root Cause Analysis (RCA)
RCA is enabled through the `Reflector` which logs failures and integrates human verdicts back into the `KnowledgeRepository`, enabling the `QAChatAgent` to explain divergences based on historical data.
