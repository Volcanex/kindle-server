# Project Development Rules

## Core Principles
1. **Strict Tree Structure**: The project follows a hierarchical tree structure with data flowing only up and down branches, never across.
2. **Modular Design**: Each directory is a self-contained module with clear boundaries and responsibilities.
3. **Upward Dependencies Only**: Modules can only depend on themselves or their parent modules, never on siblings or children. Aside from simple global dependencies (packages, venv ect)

## File Organization Rules
1. **Required Documentation Files**:
   - `rules.md`: Defines rules for everything beneath the current directory
   - `readme.md`: Describes the immediate subdirectories and their purposes
   - `patterns.md`: Documents design patterns and architectural decisions
   - `approach.md`: Required in task directories to describe the task
   - `notes.md`: Required after task completion to document outcomes

2. **File Size Limits**:
   - Maximum 3000 lines per file
   - Split large modules into logical submodules when approaching this limit

## Dependency Management
1. **Global Dependencies**:
   - Virtual environment at project root (`/home/gabriel/Desktop/obfuscation/`)
   - Common packages in root `requirements.txt`
   - Only truly universal dependencies (numpy, standard utils)

2. **Local Dependencies**:
   - Complex or specialized dependencies bundled within relevant modules
   - Each module may have its own `requirements.txt`
   - Dependencies must be justified and documented

3. **Shared Utilities**:
   - Place at the lowest common ancestor of all modules that use them
   - Never place higher than necessary
   - Document usage in `patterns.md`

## Data Flow Rules
1. **Vertical Communication Only**:
   - Data flows up through return values and interfaces
   - Data flows down through function parameters and configuration
   - No lateral communication between sibling modules

2. **Module Communication**:
   - Modules communicate at their lowest shared intersection
   - Use manager pattern for cross-branch communication
   - Document communication patterns in `patterns.md`

## Configuration Management
1. **Configuration Scope**:
   - Configuration files live at the lowest level that uses them
   - No configuration file should be placed higher than necessary
   - Environment-specific configs use `.env` pattern

## Testing Rules
1. **Unit Tests**:
   - Each module contains its own unit tests
   - Tests live in `tests/` subdirectory within the module

2. **Integration Tests**:
   - Located at the intersection point of modules being tested
   - Follow the same tree structure principle

## Version Control
1. **Git Best Practices**:
   - Atomic commits with clear messages
   - Feature branches for new modules
   - PR reviews must verify tree structure compliance
   - No commits that violate dependency rules

## Development Workflow
1. **Task Execution**:
   - Read parent `rules.md` and `structure.md` before starting
   - Create task directory in appropriate `tasks/` folder
   - Write `approach.md` before implementation
   - Write `notes.md` after completion

2. **Directory Navigation**:
   - Always check/create `rules.md`, `readme.md`, and `patterns.md` when entering new directories
   - Verify compliance with parent rules
   - Document any patterns or architectural decisions

## Logging and Monitoring
1. **Unified Logging System**:
   - All modules use centralized logging from `core/utils/logging.py`
   - Hierarchical logger names follow module path (e.g., `detection.binoculars`)
   - Log levels: DEBUG (detailed), INFO (progress), WARNING, ERROR

2. **Log Flow Architecture**:
   - Logs flow upward through module hierarchy to GUI console
   - Background operations (model loading) must include detailed logging
   - Thread-safe logging for concurrent operations

3. **GUI Integration**:
   - Real-time log display in GUI console tab
   - Error visibility for debugging slow or hanging operations
   - Auto-scroll and clear console functionality

4. **Logging Standards**:
   - Module initialization: `logger.info("ModuleName initialized")`
   - Model loading: Progress messages at each step
   - Error handling: `logger.error(f"Operation failed: {error}")`
   - Debug info: Detailed internal state when needed

## Code Quality
1. **Modularity**:
   - Single responsibility per module
   - Clear interfaces between modules
   - Minimal coupling, maximum cohesion

2. **Documentation**:
   - Self-documenting code with clear naming
   - API documentation for public interfaces
   - Examples in `patterns.md` where applicable