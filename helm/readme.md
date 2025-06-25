# AI Text Detection & Humanization Library

## Overview
This project implements an AI text detection and humanization library using a strict hierarchical tree structure. All components follow upward-only dependencies with vertical data flow.

## Key Research Tools & Frameworks

### Detection Tools
1. **RADAR (IBM)** - Most robust detector using adversarial training across 8 LMs, resistant to paraphrasing attacks
2. **Binoculars (ICML 2024)** - Zero-shot domain-agnostic detection via probability curvature analysis
3. **FastStylometry** - Burrows' Delta algorithm for authorship attribution and writing style analysis
4. **RAID Benchmark** - Comprehensive evaluation framework with 10M+ documents across 11 LMs

### Humanization/Enhancement Tools
1. **TextAttack** - 16+ attack recipes (TextFooler, BERT-Attack, BAE) with quality constraints
2. **OpenAttack** - 12+ models covering word, character, sentence-level perturbations  
3. **Adversarial Paraphrasing** - Research-based approach achieving 87.88% detection reduction
4. **par4Acad** - Academic writing style improvement preserving citations and accuracy

### Specialized Tools
- **Fibber** - Advanced semantic-preserving paraphrasing attacks
- **Stegano** - Steganographic text hiding approaches
- **AI Text Humanizer App** - Practical academic writing enhancement

### Key Capabilities
- Quality preservation through semantic similarity constraints
- Multi-level attacks (character, word, sentence)
- Evaluation frameworks for measuring evasion success rates
- Academic text optimization maintaining formal writing standards

## Root Level Structure

### `/project/`
The main implementation directory containing all functional modules.

**Expected Subdirectories:**
- `core/` - Foundation modules (text processing, utilities)
- `detection/` - AI text detection components
- `humanization/` - Text humanization components
- `api/` - Top-level API and manager interfaces
- `gui/` - User interface components (if applicable)

### `/helm/`
Project-wide governance and documentation.

**Contents:**
- `rules.md` - Development rules for entire project
- `structure.md` - This file
- `system_prompt.md` - AI guidance instructions
- `tasks/` - Task tracking and documentation

### Project Root Files
- `.gitignore` - Version control exclusions
- `requirements.txt` - Global Python dependencies
- `venv/` or `.venv/` - Virtual environment
- `README.md` - Project overview and setup

## Module Organization Principles

### Core Modules (`/project/core/`)
- Text preprocessing utilities
- Common data structures
- Shared algorithms (at appropriate level)
- Base classes and interfaces

### Detection Modules (`/project/detection/`)
- Feature extraction components
- Statistical analysis tools
- ML model interfaces
- Detection algorithms

### Humanization Modules (`/project/humanization/`)
- Text transformation engines
- Style transfer components
- Variation generators
- Quality assessment tools

### API Layer (`/project/api/`)
- High-level interfaces
- Module orchestration
- Data flow management
- Result aggregation

## Data Flow Architecture

```
        API Layer
           |
    +------+------+
    |             |
Detection    Humanization
    |             |
    +------+------+
           |
        Core
```

Data flows vertically through well-defined interfaces. Cross-branch communication happens only through the API layer manager.

## Technology Stack
- **Language**: Python 3.8+
- **ML Framework**: TBD based on requirements
- **Testing**: pytest
- **Documentation**: Markdown + docstrings
- **Version Control**: Git

## Development Patterns
- Manager pattern for cross-module coordination
- Factory pattern for model instantiation
- Strategy pattern for swappable algorithms
- Observer pattern for progress tracking

Each module will contain its own `readme.md` detailing its specific subdirectories and organization, plus `patterns.md` documenting architectural decisions.