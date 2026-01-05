# Contributing to Turkish Diaspora App

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd turkish-diaspora-app
   ```

2. **Follow the Quick Start Guide**
   - See [`QUICK_START.md`](./QUICK_START.md) for complete setup instructions
   - Copy `.env.template` to `Backend/.env` and configure required secrets
   - Set up the frontend environment variables in `Frontend/.env.development`

3. **Backend Setup**
   ```bash
   cd Backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

4. **Frontend Setup**
   ```bash
   cd Frontend
   npm install
   npm run dev
   ```

## Code Style

### Python (Backend)

- Use **async/await** for all I/O operations
- Follow **FastAPI patterns** with Pydantic models
- Use **structured logging** with `app.core.logging`
- **Type hints required** for all functions
- Follow PEP 8 style guidelines
- Use `black` for code formatting (if configured)

### TypeScript (Frontend)

- Use **React hooks** and functional components
- **TypeScript strict mode** enabled - all types must be explicit
- Use **Tailwind CSS** for styling with component-based design
- API calls through `lib/api/` layer
- State management with React hooks (useState, useEffect, useMemo)
- Follow existing code patterns and component structure

## Testing

- Run linting/tests relevant to touched areas before committing
- Workers should be exercised with `--dry-run` flags locally
- Frontend: Run `npm run build` to check for TypeScript errors
- Backend: Use pytest for unit tests (if available)

## Pull Request Process

1. **Create a branch** from `main` (or appropriate base branch)
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, maintainable code
   - Update documentation if needed
   - Ensure all linter errors are resolved

3. **Commit your changes**
   - Write clear, descriptive commit messages
   - Reference issue numbers if applicable
   - Example: `feat: add user profile page (#123)`

4. **Push and create a PR**
   - Push your branch to the repository
   - Create a pull request with a clear description
   - Reference any related issues

5. **PR Requirements**
   - All linter errors must be resolved
   - Code must follow style guidelines
   - Documentation should be updated if features are added/changed
   - Tests should pass (if applicable)

## Documentation

- Keep documentation in sync with code changes
- Update `Docs/env-config.md` when adding new environment variables
- Update `Docs/README.md` when adding new documentation files
- Update `PROJECT_PROGRESS.md` for major feature completions
- Follow the existing documentation structure and style

## Project Structure

- `Backend/` - FastAPI service, workers, services
- `Frontend/` - React/Vite application
- `Docs/` - Project documentation
- `Infra/` - Database migrations, configuration files
- `.github/workflows/` - CI/CD automation

## Getting Help

- Check [`Docs/runbook.md`](./Docs/runbook.md) for operational guidance
- Review [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) for architecture overview
- Open an issue for questions or discussions
- Reach out to maintainers (see `owners` in doc front matter)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

Thank you for contributing! 🎉



