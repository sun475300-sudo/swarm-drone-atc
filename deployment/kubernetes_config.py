"""Kubernetes Orchestration Module for Phase 240-259.

Provides Kubernetes deployment and orchestration capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DeploymentStrategy(Enum):
    """K8s deployment strategies."""

    ROLLING = "RollingUpdate"
    RECREATE = "Recreate"
    BLUE_GREEN = "BlueGreen"
    CANARY = "Canary"


class ResourceType(Enum):
    """Kubernetes resource types."""

    DEPLOYMENT = "Deployment"
    SERVICE = "Service"
    INGRESS = "Ingress"
    CONFIGMAP = "ConfigMap"
    SECRET = "Secret"
    PVC = "PersistentVolumeClaim"


@dataclass
class ContainerSpec:
    """Container specification."""

    name: str
    image: str
    port: int
    cpu_request: str = "100m"
    memory_request: str = "128Mi"
    cpu_limit: str = "500m"
    memory_limit: str = "512Mi"


@dataclass
class DeploymentSpec:
    """K8s deployment specification."""

    name: str
    namespace: str
    replicas: int
    strategy: DeploymentStrategy
    containers: list[ContainerSpec]


class KubernetesOrchestrator:
    """Manages Kubernetes deployments."""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.deployments: dict[str, DeploymentSpec] = {}
        self.services: dict[str, dict] = {}

    def create_deployment(
        self,
        name: str,
        image: str,
        replicas: int = 3,
    ) -> DeploymentSpec:
        """Create a deployment specification."""
        container = ContainerSpec(
            name=name,
            image=image,
            port=8000,
        )

        spec = DeploymentSpec(
            name=name,
            namespace=self.namespace,
            replicas=replicas,
            strategy=DeploymentStrategy.ROLLING,
            containers=[container],
        )

        self.deployments[name] = spec
        return spec

    def create_service(
        self,
        name: str,
        service_type: str = "ClusterIP",
        port: int = 80,
        target_port: int = 8000,
    ) -> dict:
        """Create a service specification."""
        service = {
            "name": name,
            "type": service_type,
            "port": port,
            "target_port": target_port,
        }
        self.services[name] = service
        return service

    def generate_manifests(self) -> dict[str, str]:
        """Generate Kubernetes YAML manifests."""
        manifests = {}

        for name, deploy in self.deployments.items():
            manifests[f"{name}-deployment.yaml"] = self._generate_deployment_yaml(
                deploy
            )

        for name, service in self.services.items():
            manifests[f"{name}-service.yaml"] = self._generate_service_yaml(service)

        return manifests

    def _generate_deployment_yaml(self, spec: DeploymentSpec) -> str:
        """Generate deployment YAML."""
        container = spec.containers[0]
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {spec.name}
  namespace: {spec.namespace}
spec:
  replicas: {spec.replicas}
  strategy:
    type: {spec.strategy.value}
  selector:
    matchLabels:
      app: {spec.name}
  template:
    metadata:
      labels:
        app: {spec.name}
    spec:
      containers:
      - name: {container.name}
        image: {container.image}
        ports:
        - containerPort: {container.port}
        resources:
          requests:
            cpu: {container.cpu_request}
            memory: {container.memory_request}
          limits:
            cpu: {container.cpu_limit}
            memory: {container.memory_limit}
"""

    def _generate_service_yaml(self, service: dict) -> str:
        """Generate service YAML."""
        return f"""apiVersion: v1
kind: Service
metadata:
  name: {service["name"]}
spec:
  type: {service["type"]}
  selector:
    app: {service["name"]}
  ports:
  - port: {service["port"]}
    targetPort: {service["target_port"]}
"""


def create_atc_cluster() -> KubernetesOrchestrator:
    """Create ATC cluster configuration."""
    orchestrator = KubernetesOrchestrator(namespace="sdacs")

    orchestrator.create_deployment(
        name="sdacs-api",
        image="sdacs/api:latest",
        replicas=3,
    )

    orchestrator.create_deployment(
        name="sdacs-controller",
        image="sdacs/controller:latest",
        replicas=2,
    )

    orchestrator.create_service(
        name="sdacs-api",
        service_type="LoadBalancer",
        port=80,
        target_port=8000,
    )

    return orchestrator
