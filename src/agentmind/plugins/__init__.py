"""
AgentMind Plugin System - Production-Grade Features

This module provides a comprehensive plugin system with:
- Lifecycle management with hooks
- Dependency resolution and version checking
- Security features (sandboxing, permissions, signatures)
- Configuration management with hot-reload
- Plugin marketplace infrastructure
- Audit logging
- Testing utilities
"""

from .base import (
    Plugin,
    PluginType,
    PluginMetadata,
    PluginConfig,
    ToolPlugin,
    IntegrationPlugin,
    MemoryPlugin,
    LLMProviderPlugin,
    OrchestrationPlugin,
    MiddlewarePlugin,
    UIPlugin,
)

from .manager import PluginManager
from .loader import PluginLoader, PluginRegistry
from .discovery import PluginDiscovery, discover_plugins, load_plugin, list_plugins

from .lifecycle import (
    PluginLifecycleManager,
    PluginState,
    HealthStatus,
    LifecycleHooks,
)

from .dependencies import (
    DependencyResolver,
    PluginDependency,
    DependencyGraph,
    VersionChecker,
)

from .security import (
    PermissionManager,
    PluginPermissions,
    PluginPermission,
    SandboxExecutor,
    ResourceLimits,
    SignatureVerifier,
    PluginSignature,
    require_permission,
)

from .config import (
    ConfigManager,
    ConfigEnvironment,
    PluginConfigSchema,
    ConfigValidator,
)

from .marketplace import (
    PluginRegistry as MarketplaceRegistry,
    PluginManifest,
    PluginCategory,
    PluginRating,
)

from .audit import (
    PluginAuditLogger,
    AuditEvent,
    AuditEventType,
    log_plugin_loaded,
    log_plugin_error,
    log_permission_denied,
    log_config_changed,
)

from .testing import (
    MockPlugin,
    FailingPlugin,
    PluginTestHarness,
    create_test_plugin,
    run_plugin_test_suite,
    assert_plugin_valid,
    PluginPerformanceTester,
)

__all__ = [
    # Base classes
    "Plugin",
    "PluginType",
    "PluginMetadata",
    "PluginConfig",
    "ToolPlugin",
    "IntegrationPlugin",
    "MemoryPlugin",
    "LLMProviderPlugin",
    "OrchestrationPlugin",
    "MiddlewarePlugin",
    "UIPlugin",
    # Core management
    "PluginManager",
    "PluginLoader",
    "PluginRegistry",
    "PluginDiscovery",
    "discover_plugins",
    "load_plugin",
    "list_plugins",
    # Lifecycle
    "PluginLifecycleManager",
    "PluginState",
    "HealthStatus",
    "LifecycleHooks",
    # Dependencies
    "DependencyResolver",
    "PluginDependency",
    "DependencyGraph",
    "VersionChecker",
    # Security
    "PermissionManager",
    "PluginPermissions",
    "PluginPermission",
    "SandboxExecutor",
    "ResourceLimits",
    "SignatureVerifier",
    "PluginSignature",
    "require_permission",
    # Configuration
    "ConfigManager",
    "ConfigEnvironment",
    "PluginConfigSchema",
    "ConfigValidator",
    # Marketplace
    "MarketplaceRegistry",
    "PluginManifest",
    "PluginCategory",
    "PluginRating",
    # Audit
    "PluginAuditLogger",
    "AuditEvent",
    "AuditEventType",
    "log_plugin_loaded",
    "log_plugin_error",
    "log_permission_denied",
    "log_config_changed",
    # Testing
    "MockPlugin",
    "FailingPlugin",
    "PluginTestHarness",
    "create_test_plugin",
    "run_plugin_test_suite",
    "assert_plugin_valid",
    "PluginPerformanceTester",
]
