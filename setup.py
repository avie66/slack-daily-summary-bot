from setuptools import setup, find_packages

setup(
    name="slack_daily_summary",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit",
        "slack-sdk",
        "slack-bolt",
    ],
    package_data={
        "": ["*.webp", "*.png", "*.html", "*.lark", "*.json"],
    },
)
