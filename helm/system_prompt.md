# AI Text Detection & Humanization Library Development

## Project Overview
We are developing a server to sync files with a kindle. The server should compile daily news interests and should be able to store books uploaded to it. Whenever it syncs with the kindle, the kindle will download it. We need to develop the server container, a frontend and a KUAL plugin. We should use the free google e2 instance. 

## Development Methodology
We use a software methodology that embeds AI guidance into code structure following a strict tree architecture.

### Getting Started
Always start by reading:
1. `/home/gabriel/Desktop/kindle/helm/rules.md` - Development rules that must not be broken
2. `/home/gabriel/Desktop/kindle/helm/readme.md` - This should be used to keep track of the current state of the project.
3. `/home/gabriel/Desktop/kindle/readme.md;` this should be used for the overall design and the tech stack.

### Project Structure
Work in `/home/gabriel/Desktop/kindle/project` where each directory contains:
- `rules.md` - Rules for everything beneath the current directory
- `readme.md` - Describes immediate subdirectories and their purposes
- `patterns.md` - Architectural patterns and design decisions

### Tree Architecture Principles
- **Strict hierarchy**: Data flows only up and down branches, never across
- **Upward dependencies**: Modules depend only on themselves or parent modules
- **Shared utilities**: Placed at lowest common ancestor, no higher
- **Module communication**: Happens at lowest shared intersection point
- **Build deep file structures**: We want components to maintain isolation so we can see very clearly where the issues are. 
- **Sub-agents**: Sub agents can be used to work on parts of the tree, so long as no other agent is working below it. They can use git branches to maintain isolation until code changes are complete. Ideally data transfer formats shouldn't change too often, and if they are they should be additive as to not break backwards compatbility, this means we can have multiple sub-agents working simultaniously.  

## Workflow
1. Read rules and readme files ect
2. Create new directory in `tasks/` for the task
3. Write `approach.md` describing the task briefly
4. Create internal checklist (note in approach.md)
5. When entering new project directories, check/create rules.md, readme.md, and patterns.md
6. Write `notes.md` after completion
7. Commit changes to the git in the top level folder /home/gabriel/Desktop/kindle/.git, then start a new task. Ask for explicit permission before finishing a task in this way. 

Sub-agents should always work on different tasks. They should never work on the same part of the program at the same time. 

## Key Architectural Principles
- Global dependencies (virtual environments, root requirements.txt) permitted at project root
- Simple dependencies applied globally, complex ones bundled within modules
- Integration tests at module intersection points
- Configuration files at lowest usage level
- Maximum 3000 lines per file
- Standard Git practices with tree structure compliance