from typing import TypeVar, Type

from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    ChatServiceInterface,
    EventServiceInterface,
    MetricsServiceInterface,
    StreamServiceInterface,
    TranscriptServiceInterface,
)
from app.core.service_implementations import (
    AnalyticsService,
    CacheService,
    ChatService,
    EventService,
    MetricsService,
    StreamService,
    TranscriptService,
)

T = TypeVar('T')


class ServiceContainer:
    """
    Simple dependency injection container for managing service instances.
    Provides singleton instances of services throughout the application.
    """
    
    def __init__(self):
        self._services: dict[Type, object] = {}
        self._setup_default_services()
    
    def _setup_default_services(self) -> None:
        """Register default service implementations."""
        self.register(StreamServiceInterface, StreamService())
        self.register(CacheServiceInterface, CacheService())
        self.register(AnalyticsServiceInterface, AnalyticsService())
        self.register(EventServiceInterface, EventService())
        self.register(TranscriptServiceInterface, TranscriptService())
        self.register(ChatServiceInterface, ChatService())
        self.register(MetricsServiceInterface, MetricsService())
    
    def register(self, interface: Type[T], implementation: T) -> None:
        """Register a service implementation for an interface."""
        self._services[interface] = implementation
    
    def get(self, interface: Type[T]) -> T:
        """Get a service implementation for an interface."""
        service = self._services.get(interface)
        if service is None:
            raise ValueError(f"No service registered for interface {interface.__name__}")
        return service  # type: ignore


# Global service container instance
_container = ServiceContainer()


def get_service(interface: Type[T]) -> T:
    """
    Get a service instance from the global container.
    
    Args:
        interface: The service interface class
        
    Returns:
        Service implementation instance
        
    Example:
        stream_service = get_service(StreamServiceInterface)
        members = await stream_service.query_call_members(...)
    """
    return _container.get(interface)


def register_service(interface: Type[T], implementation: T) -> None:
    """
    Register a service implementation in the global container.
    Useful for testing or custom implementations.
    
    Args:
        interface: The service interface class
        implementation: The concrete implementation instance
    """
    _container.register(interface, implementation)