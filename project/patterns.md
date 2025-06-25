# Architectural Patterns

## Manager Pattern
- **API Manager**: Orchestrates communication between backend, frontend, and kindle modules
- **Sync Manager**: Coordinates content synchronization across devices
- **Storage Manager**: Handles file operations with Cloud Storage

## Factory Pattern
- **Content Factory**: Creates different content types (news, books, sync packages)
- **Export Factory**: Generates various file formats (EPUB, PDF, etc.)
- **Sync Protocol Factory**: Creates sync handlers for different Kindle firmware versions

## Strategy Pattern
- **News Source Strategy**: Pluggable RSS feed processors
- **Content Conversion Strategy**: Multiple format conversion algorithms
- **Sync Strategy**: Different synchronization methods based on device capabilities

## Observer Pattern
- **Progress Tracking**: Real-time updates for long-running operations
- **Sync Status**: Device synchronization status monitoring
- **Error Notification**: System-wide error reporting

## Data Flow Architecture

```
Mobile App (React Native)
        ↓ HTTPS API
    API Manager
        ↓
┌─────────┬─────────┬─────────┐
│ Backend │Frontend │ Kindle  │
│ Service │ Service │ Service │
└─────────┴─────────┴─────────┘
        ↓
   Cloud Storage
   Cloud SQL
```

## Security Patterns
- **IAM Role Separation**: Minimal permissions per service
- **API Authentication**: JWT tokens for mobile app
- **Device Authentication**: Unique Kindle device IDs
- **Data Encryption**: At rest and in transit

## Concurrency Patterns
- **Sub-Agent Isolation**: Different git branches for parallel development
- **Backwards Compatible APIs**: Additive changes only
- **Async Operations**: Background tasks for news aggregation and content processing