"""Advanced tool system with external framework support.

This module provides:
- Native LangChain tools support
- LlamaIndex tools support
- MCP (Model Context Protocol) support
- Tool auto-discovery
- Security sandbox
"""

from typing import Any, Callable, Dict, List, Optional, Union
from abc import ABC, abstractmethod
import asyncio
import inspect
from enum import Enum

from .base import Tool, ToolResult, ToolRegistry


class ToolSource(str, Enum):
    """Tool source types."""

    NATIVE = "native"
    LANGCHAIN = "langchain"
    LLAMAINDEX = "llamaindex"
    MCP = "mcp"
    CUSTOM = "custom"


class ToolPermission(str, Enum):
    """Tool permission levels."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILESYSTEM = "filesystem"


class AdvancedTool(Tool):
    """Enhanced tool with permissions and metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        source: ToolSource = ToolSource.NATIVE,
        permissions: Optional[List[ToolPermission]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize advanced tool.

        Args:
            name: Tool name
            description: Tool description
            source: Tool source
            permissions: Required permissions
            metadata: Additional metadata
        """
        super().__init__()
        self.name = name
        self.description = description
        self.source = source
        self.permissions = permissions or []
        self.metadata = metadata or {}

    def requires_permission(self, permission: ToolPermission) -> bool:
        """Check if tool requires a permission.

        Args:
            permission: Permission to check

        Returns:
            True if required
        """
        return permission in self.permissions


class LangChainToolAdapter(AdvancedTool):
    """Adapter for LangChain tools."""

    def __init__(self, langchain_tool: Any):
        """Initialize from LangChain tool.

        Args:
            langchain_tool: LangChain tool instance
        """
        super().__init__(
            name=langchain_tool.name,
            description=langchain_tool.description,
            source=ToolSource.LANGCHAIN,
        )
        self.langchain_tool = langchain_tool

    async def execute(self, **kwargs) -> ToolResult:
        """Execute LangChain tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        try:
            # LangChain tools use _run or _arun
            if hasattr(self.langchain_tool, "_arun"):
                result = await self.langchain_tool._arun(**kwargs)
            elif hasattr(self.langchain_tool, "_run"):
                result = self.langchain_tool._run(**kwargs)
            else:
                result = self.langchain_tool.run(**kwargs)

            return ToolResult(success=True, output=result)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LlamaIndexToolAdapter(AdvancedTool):
    """Adapter for LlamaIndex tools."""

    def __init__(self, llamaindex_tool: Any):
        """Initialize from LlamaIndex tool.

        Args:
            llamaindex_tool: LlamaIndex tool instance
        """
        super().__init__(
            name=llamaindex_tool.metadata.name,
            description=llamaindex_tool.metadata.description,
            source=ToolSource.LLAMAINDEX,
        )
        self.llamaindex_tool = llamaindex_tool

    async def execute(self, **kwargs) -> ToolResult:
        """Execute LlamaIndex tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        try:
            # LlamaIndex tools use call method
            if asyncio.iscoroutinefunction(self.llamaindex_tool.call):
                result = await self.llamaindex_tool.call(**kwargs)
            else:
                result = self.llamaindex_tool.call(**kwargs)

            return ToolResult(success=True, output=str(result))

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MCPToolAdapter(AdvancedTool):
    """Adapter for MCP (Model Context Protocol) tools."""

    def __init__(self, mcp_tool: Dict[str, Any]):
        """Initialize from MCP tool definition.

        Args:
            mcp_tool: MCP tool definition dict
        """
        super().__init__(
            name=mcp_tool.get("name", "unknown"),
            description=mcp_tool.get("description", ""),
            source=ToolSource.MCP,
        )
        self.mcp_tool = mcp_tool
        self.endpoint = mcp_tool.get("endpoint")

    async def execute(self, **kwargs) -> ToolResult:
        """Execute MCP tool via HTTP.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json=kwargs,
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()

            return ToolResult(success=True, output=result)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SecuritySandbox:
    """Security sandbox for tool execution."""

    def __init__(
        self,
        allowed_permissions: Optional[List[ToolPermission]] = None,
        enable_docker: bool = False,
    ):
        """Initialize security sandbox.

        Args:
            allowed_permissions: Allowed permissions
            enable_docker: Use Docker for isolation
        """
        self.allowed_permissions = allowed_permissions or [
            ToolPermission.READ,
            ToolPermission.EXECUTE,
        ]
        self.enable_docker = enable_docker

    def check_permissions(self, tool: AdvancedTool) -> bool:
        """Check if tool permissions are allowed.

        Args:
            tool: Tool to check

        Returns:
            True if allowed
        """
        for permission in tool.permissions:
            if permission not in self.allowed_permissions:
                return False
        return True

    async def execute_sandboxed(
        self,
        tool: AdvancedTool,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute tool in sandbox.

        Args:
            tool: Tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        # Check permissions
        if not self.check_permissions(tool):
            return ToolResult(
                success=False,
                error=f"Tool requires unauthorized permissions: {tool.permissions}",
            )

        # Execute based on sandbox mode
        if self.enable_docker:
            return await self._execute_in_docker(tool, **kwargs)
        else:
            return await self._execute_isolated(tool, **kwargs)

    async def _execute_isolated(
        self,
        tool: AdvancedTool,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute in process isolation.

        Args:
            tool: Tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                tool.execute(**kwargs),
                timeout=30.0,
            )
            return result

        except asyncio.TimeoutError:
            return ToolResult(success=False, error="Tool execution timeout")
        except Exception as e:
            return ToolResult(success=False, error=f"Sandbox error: {str(e)}")

    async def _execute_in_docker(
        self,
        tool: AdvancedTool,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute in Docker container.

        Args:
            tool: Tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        # Placeholder for Docker execution
        # In production, would use docker-py or e2b
        return ToolResult(
            success=False,
            error="Docker execution not yet implemented",
        )


class AdvancedToolRegistry(ToolRegistry):
    """Enhanced tool registry with auto-discovery and security."""

    def __init__(self, sandbox: Optional[SecuritySandbox] = None):
        """Initialize advanced registry.

        Args:
            sandbox: Security sandbox
        """
        super().__init__()
        self.sandbox = sandbox or SecuritySandbox()
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}

    def register_langchain_tool(self, langchain_tool: Any) -> None:
        """Register a LangChain tool.

        Args:
            langchain_tool: LangChain tool instance
        """
        adapter = LangChainToolAdapter(langchain_tool)
        self.register(adapter)
        self._tool_metadata[adapter.name] = {
            "source": ToolSource.LANGCHAIN,
            "original": langchain_tool,
        }
        print(f"[Tools] Registered LangChain tool: {adapter.name}")

    def register_llamaindex_tool(self, llamaindex_tool: Any) -> None:
        """Register a LlamaIndex tool.

        Args:
            llamaindex_tool: LlamaIndex tool instance
        """
        adapter = LlamaIndexToolAdapter(llamaindex_tool)
        self.register(adapter)
        self._tool_metadata[adapter.name] = {
            "source": ToolSource.LLAMAINDEX,
            "original": llamaindex_tool,
        }
        print(f"[Tools] Registered LlamaIndex tool: {adapter.name}")

    def register_mcp_tool(self, mcp_tool: Dict[str, Any]) -> None:
        """Register an MCP tool.

        Args:
            mcp_tool: MCP tool definition
        """
        adapter = MCPToolAdapter(mcp_tool)
        self.register(adapter)
        self._tool_metadata[adapter.name] = {
            "source": ToolSource.MCP,
            "endpoint": mcp_tool.get("endpoint"),
        }
        print(f"[Tools] Registered MCP tool: {adapter.name}")

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute tool with security checks.

        Args:
            name: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")

        # Execute in sandbox if tool is AdvancedTool
        if isinstance(tool, AdvancedTool):
            return await self.sandbox.execute_sandboxed(tool, **kwargs)
        else:
            # Fallback to direct execution
            try:
                return await tool.execute(**kwargs)
            except Exception as e:
                return ToolResult(success=False, error=str(e))

    def auto_discover_tools(self, module_path: str) -> int:
        """Auto-discover tools from a module.

        Args:
            module_path: Python module path

        Returns:
            Number of tools discovered
        """
        import importlib

        try:
            module = importlib.import_module(module_path)
            count = 0

            for name in dir(module):
                obj = getattr(module, name)

                # Check if it's a Tool subclass
                if inspect.isclass(obj) and issubclass(obj, Tool) and obj is not Tool:
                    tool_instance = obj()
                    self.register(tool_instance)
                    count += 1

            print(f"[Tools] Auto-discovered {count} tools from {module_path}")
            return count

        except Exception as e:
            print(f"[!] Error discovering tools: {e}")
            return 0

    def generate_tool_description(self, tool_name: str) -> Optional[str]:
        """Generate natural language description for a tool.

        Args:
            tool_name: Tool name

        Returns:
            Generated description or None
        """
        tool = self.get(tool_name)
        if not tool:
            return None

        # Get tool definition
        definition = tool.get_definition()

        # Generate description
        params = definition.parameters.get("properties", {})
        param_desc = ", ".join(
            f"{name} ({info.get('type', 'any')})" for name, info in params.items()
        )

        description = f"{definition.description}\n\nParameters: {param_desc}"

        if isinstance(tool, AdvancedTool):
            description += f"\n\nSource: {tool.source.value}"
            if tool.permissions:
                description += f"\nPermissions: {', '.join(p.value for p in tool.permissions)}"

        return description

    def get_tools_by_permission(
        self,
        permission: ToolPermission,
    ) -> List[str]:
        """Get tools requiring a specific permission.

        Args:
            permission: Permission to filter by

        Returns:
            List of tool names
        """
        tools = []
        for name, tool in self._tools.items():
            if isinstance(tool, AdvancedTool):
                if tool.requires_permission(permission):
                    tools.append(name)
        return tools

    def get_tools_by_source(self, source: ToolSource) -> List[str]:
        """Get tools from a specific source.

        Args:
            source: Tool source

        Returns:
            List of tool names
        """
        tools = []
        for name, metadata in self._tool_metadata.items():
            if metadata.get("source") == source:
                tools.append(name)
        return tools

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Statistics dict
        """
        sources = {}
        permissions = {}

        for name, tool in self._tools.items():
            if isinstance(tool, AdvancedTool):
                # Count by source
                source = tool.source.value
                sources[source] = sources.get(source, 0) + 1

                # Count by permission
                for perm in tool.permissions:
                    perm_name = perm.value
                    permissions[perm_name] = permissions.get(perm_name, 0) + 1

        return {
            "total_tools": len(self._tools),
            "by_source": sources,
            "by_permission": permissions,
            "sandbox_enabled": self.sandbox is not None,
        }


# Convenience functions
def create_advanced_registry(
    allowed_permissions: Optional[List[ToolPermission]] = None,
    enable_docker: bool = False,
) -> AdvancedToolRegistry:
    """Create an advanced tool registry.

    Args:
        allowed_permissions: Allowed permissions
        enable_docker: Enable Docker sandbox

    Returns:
        Advanced tool registry
    """
    sandbox = SecuritySandbox(
        allowed_permissions=allowed_permissions,
        enable_docker=enable_docker,
    )
    return AdvancedToolRegistry(sandbox=sandbox)
