# Project Implementation Rules

## Core Architecture Rules
1. **Strict Tree Structure**: All modules follow hierarchical structure with upward-only dependencies
2. **Vertical Data Flow**: Data flows up through return values, down through parameters
3. **Module Isolation**: Each component is self-contained with clear boundaries

## Development Rules
1. **File Size Limit**: Maximum 3000 lines per file
2. **Required Documentation**: Each directory must have rules.md, readme.md, patterns.md
3. **Dependency Management**: Place shared utilities at lowest common ancestor

## Kindle Server Specific Rules
1. **Cloud-First Design**: All components designed for Google Cloud deployment
2. **Stateless Architecture**: No local state persistence, use Cloud Storage/SQL
3. **Security Focus**: IAM permissions, encrypted data, secure endpoints
4. **Performance**: Optimize for serverless cold starts and mobile sync

## Module Communication
- Cross-branch communication only through manager patterns
- API layer orchestrates between backend, frontend, and kindle components
- Shared formats must be backwards compatible for concurrent development

## Testing Requirements
- Unit tests within each module's tests/ directory
- Integration tests at module intersection points
- End-to-end testing for sync functionality