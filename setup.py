from setuptools import setup, find_packages

setup(
    name="k8s-admission-webhook",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "kubernetes>=28.1.0",
        "pydantic>=2.4.2",
        "prometheus-client>=0.17.1",
        "cryptography>=41.0.4",
        "httpx>=0.24.1",
        "python-json-logger>=2.0.7",
        "pydantic-settings>=2.0.0",
        "gunicorn>=21.2.0",
        "uvloop>=0.19.0",
        "httptools>=0.6.1",
        "python-multipart>=0.0.9",
        "email-validator>=2.1.0",
        "slowapi>=0.1.8",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.23.5",
            "pytest-mock>=3.12.0",
            "black",
            "isort",
            "flake8",
            "mypy",
        ]
    },
    python_requires=">=3.11",
)