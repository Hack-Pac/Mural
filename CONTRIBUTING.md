# Contributing to Mural

Thank you for your interest in contributing to Mural! This document provides guidelines and information for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Contribution Types](#contribution-types)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.8+** installed
- **Git** for version control
- **Redis** (optional, for caching)
- A **GitHub account**
- Familiarity with **Flask**, **JavaScript**, and **WebSocket** concepts

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/Mural.git
   cd Mural
   ```

3. **Set up the development environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   
   # Install pre-commit hooks
   pre-commit install
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Verify setup**:
   ```bash
   python app.py
   # Visit http://localhost:5000
   ```

### Staying Updated

Keep your fork synchronized with the upstream repository:

```bash
# Add upstream remote
git remote add upstream https://github.com/original-owner/Mural.git

# Fetch upstream changes
git fetch upstream

# Merge upstream changes into your main branch
git checkout main
git merge upstream/main
```

### Feature Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following coding standards

3. **Test your changes**:

4. **Commit your changes**:

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

## Contribution Types

### Bug Reports

When reporting bugs, please include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment information** (OS, Python version, browser)
- **Error messages** or logs if available
- **Screenshots** if applicable

Use our bug report template:

```markdown
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
A clear description of what you expected to happen.

**Environment**
- OS: [e.g., Ubuntu 20.04]
- Python Version: [e.g., 3.9.7]
- Browser: [e.g., Chrome 96]
- Version: [e.g., 1.0.0]

**Additional Context**
Add any other context about the problem here.
```

### Feature Requests

For feature requests, please include:

- **Problem description**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've thought about
- **Use cases**: Who would benefit from this feature?
- **Implementation ideas**: Technical approach (optional)

### Code Contributions

We welcome contributions in these areas:

**Backend Development:**
- API endpoint improvements
- Performance optimizations
- Caching enhancements
- Security improvements
- Database integration

**Frontend Development:**
- UI/UX improvements
- Mobile responsiveness
- Accessibility features
- Performance optimizations
- New themes or visual enhancements

**DevOps & Infrastructure:**
- Docker improvements
- CI/CD enhancements
- Deployment scripts
- Monitoring tools
- Documentation

**Testing:**
- Unit tests
- Integration tests
- Performance tests
- Security tests
- Test automation

### Documentation

Documentation contributions are highly valued:

- **API documentation** improvements
- **Tutorial** creation
- **Code examples**
- **Architecture** documentation
- **Deployment guides**
- **Troubleshooting** guides

## Pull Request Process

### Before Submitting

- [ ] Code follows our style guidelines
- [ ] Self-review of your own code
- [ ] Comments added for hard-to-understand areas
- [ ] Documentation updated for API changes
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] No new warnings introduced

### PR Requirements

1. **Descriptive title** following conventional commit format
2. **Detailed description** explaining the changes
3. **Issue reference** if applicable
4. **Breaking changes** clearly documented