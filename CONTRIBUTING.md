# Contributing to TikTok Ads MCP Server

Thank you for your interest in contributing to the TikTok Ads MCP Server! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow:

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment
- Report any unacceptable behavior

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- TikTok For Business developer account
- Basic knowledge of async/await patterns in Python

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/tiktok-ads-mcp.git
   cd tiktok-ads-mcp
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your TikTok API credentials
   ```

5. **Run Tests**
   ```bash
   pytest
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-tool` - for new features
- `fix/campaign-creation-bug` - for bug fixes  
- `docs/update-readme` - for documentation
- `refactor/client-error-handling` - for refactoring

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(tools): add audience insights tool`
- `fix(client): handle rate limit errors properly`
- `docs(readme): update installation instructions`

### Code Organization

```
src/tiktok_ads_mcp/
├── server.py              # Main MCP server
├── tiktok_client.py        # TikTok API client
├── tools/                  # MCP tools modules
│   ├── __init__.py
│   ├── campaign_tools.py
│   ├── creative_tools.py
│   ├── performance_tools.py
│   ├── audience_tools.py
│   └── reporting_tools.py
└── utils/                  # Utility functions
```

## Code Style

### Formatting

We use Black for code formatting:
```bash
black .
isort .
```

### Linting

Run linting checks:
```bash
flake8
mypy .
```

### Style Guidelines

- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep line length under 88 characters (Black default)
- Use meaningful variable and function names
- Follow PEP 8 conventions

Example function with proper style:
```python
async def get_campaigns(
    self,
    status: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get campaigns for the advertiser account.
    
    Args:
        status: Filter campaigns by status (ENABLE, DISABLE, DELETE)
        limit: Maximum number of campaigns to return
        
    Returns:
        Campaign data and metadata
        
    Raises:
        Exception: If API request fails
    """
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions
- Update API documentation for new tools
- Include examples in docstrings when helpful

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   pytest
   black . && isort .
   flake8
   mypy .
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(tools): add new audience insights tool"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Pull Request Template

When creating a PR, include:

- **Description**: What changes were made and why
- **Testing**: How the changes were tested
- **Breaking Changes**: Any backward incompatible changes
- **Documentation**: Links to updated documentation
- **Checklist**: Confirm all requirements are met

### Review Process

- All PRs require at least one review
- Automated checks must pass (tests, linting, etc.)
- Address reviewer feedback promptly
- Maintain a clean git history (squash commits if needed)

## Types of Contributions

### Bug Reports

When reporting bugs:
- Use a clear, descriptive title
- Provide steps to reproduce
- Include error messages and logs
- Specify your environment (Python version, OS, etc.)

### Feature Requests

When proposing features:
- Explain the use case and benefits
- Provide examples of how it would work
- Consider backward compatibility
- Be open to alternative approaches

### Code Contributions

Focus areas where contributions are especially welcome:
- New MCP tools for TikTok Ads API endpoints
- Performance optimizations
- Better error handling and logging
- Documentation improvements
- Test coverage improvements
- Examples and tutorials

## Release Process

### Version Numbering

We follow semantic versioning (SemVer):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create release branch
5. Tag release
6. Update documentation
7. Publish to PyPI

## Getting Help

- **Documentation**: Check README.md and code comments
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers at support@adsmcp.com

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes for significant contributions
- Project documentation

Thank you for contributing to the TikTok Ads MCP Server!