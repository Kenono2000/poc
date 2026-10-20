from setuptools import setup

setup(
    name="py-libraries",
    version="0.1.0",
    py_modules=["utilities"],
    python_requires=">=3.10",
    install_requires=[
        "numpy",
        "psycopg2-binary",
        "python-dotenv",
        "langchain-core",
        "langchain-community",
        "langchain-openai",
        "langchain-text-splitters",
    ],
)
