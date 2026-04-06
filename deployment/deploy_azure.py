"""Azure Deployment Script for Phase 220-239.

Deploys SDACS to Azure App Service or Container Apps.
"""

import os
import subprocess
import sys
from pathlib import Path


AZURE_SUBSCRIPTION = os.environ.get("AZURE_SUBSCRIPTION", "default")
RESOURCE_GROUP = "sdacs-rg"
APP_SERVICE_PLAN = "sdacs-plan"
WEB_APP_NAME = "sdacs-api"
CONTAINER_IMAGE = "sdacs/api:latest"
LOCATION = "koreacentral"


def check_azure_cli():
    """Check if Azure CLI is installed."""
    try:
        subprocess.run(["az", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def login_azure():
    """Login to Azure."""
    print("Logging in to Azure...")
    subprocess.run(["az", "login"], check=True)


def create_resource_group():
    """Create Azure resource group."""
    print(f"Creating resource group: {RESOURCE_GROUP}")
    subprocess.run(
        [
            "az",
            "group",
            "create",
            "--name",
            RESOURCE_GROUP,
            "--location",
            LOCATION,
        ],
        check=True,
    )


def create_app_service_plan():
    """Create App Service plan."""
    print(f"Creating App Service plan: {APP_SERVICE_PLAN}")
    subprocess.run(
        [
            "az",
            "appservice",
            "plan",
            "create",
            "--name",
            APP_SERVICE_PLAN,
            "--resource-group",
            RESOURCE_GROUP,
            "--sku",
            "B1",
            "--is-linux",
        ],
        check=True,
    )


def create_web_app():
    """Create Azure Web App."""
    print(f"Creating Web App: {WEB_APP_NAME}")
    subprocess.run(
        [
            "az",
            "webapp",
            "create",
            "--name",
            WEB_APP_NAME,
            "--resource-group",
            RESOURCE_GROUP,
            "--plan",
            APP_SERVICE_PLAN,
            "--runtime",
            "PYTHON:3.11",
        ],
        check=True,
    )


def deploy_docker():
    """Deploy Docker container."""
    print(f"Deploying Docker image: {CONTAINER_IMAGE}")
    subprocess.run(
        [
            "az",
            "webapp",
            "config",
            "container",
            "set",
            "--name",
            WEB_APP_NAME,
            "--resource-group",
            RESOURCE_GROUP,
            "--docker-custom-image-name",
            CONTAINER_IMAGE,
            "--docker-registry-server-url",
            "https://index.docker.io",
        ],
        check=True,
    )


def deploy_zip():
    """Deploy as ZIP package."""
    print("Deploying as ZIP package...")
    subprocess.run(
        [
            "az",
            "webapp",
            "deployment",
            "source",
            "config-zip",
            "--src",
            "package.zip",
            "--name",
            WEB_APP_NAME,
            "--resource-group",
            RESOURCE_GROUP,
        ],
        check=True,
    )


def get_deployment_status():
    """Get deployment status."""
    result = subprocess.run(
        [
            "az",
            "webapp",
            "show",
            "--name",
            WEB_APP_NAME,
            "--resource-group",
            RESOURCE_GROUP,
            "--query",
            "state",
        ],
        capture_output=True,
        text=True,
    )
    print(f"Deployment state: {result.stdout.strip()}")


def main():
    """Main deployment function."""
    if not check_azure_cli():
        print("Error: Azure CLI is not installed.")
        sys.exit(1)

    print("=" * 50)
    print("SDACS Azure Deployment")
    print("=" * 50)

    create_resource_group()
    create_app_service_plan()
    create_web_app()
    get_deployment_status()

    print("=" * 50)
    print(f"Deployment complete!")
    print(f"Web App URL: https://{WEB_APP_NAME}.azurewebsites.net")
    print("=" * 50)


if __name__ == "__main__":
    main()
