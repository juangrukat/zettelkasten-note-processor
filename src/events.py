"""
Event System
=============

A simple event system for decoupled communication between components.
"""

from typing import Callable, Dict, List, Any
from enum import Enum, auto


class EventType(Enum):
    """Available event types."""
    STATUS_UPDATED = auto()
    ERROR_OCCURRED = auto()
    PROCESSING_STARTED = auto()
    PROCESSING_COMPLETED = auto()
    NOTE_SAVED = auto()


class Event:
    """Base event class."""
    
    def __init__(self, event_type: EventType, data: Any = None):
        self.event_type = event_type
        self.data = data


class EventDispatcher:
    """Manages event registration and dispatch."""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable[[Event], None]]] = {}
    
    def add_listener(
        self, 
        event_type: EventType, 
        listener: Callable[[Event], None]
    ) -> None:
        """
        Add a listener for a specific event type.
        
        Args:
            event_type: Type of event to listen for
            listener: Callback function to be called when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
    
    def remove_listener(
        self, 
        event_type: EventType, 
        listener: Callable[[Event], None]
    ) -> None:
        """
        Remove a listener for a specific event type.
        
        Args:
            event_type: Type of event the listener is registered for
            listener: Callback function to remove
        """
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(listener)
                if not self._listeners[event_type]:
                    del self._listeners[event_type]
            except ValueError:
                pass
    
    def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all registered listeners.
        
        Args:
            event: Event object to dispatch
        """
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                try:
                    listener(event)
                except Exception as e:
                    # Catch and log errors to prevent listener failures from breaking dispatcher
                    print(f"Error in event listener: {e}")
    
    def dispatch_status(self, message: str) -> None:
        """
        Convenience method to dispatch a status update event.
        
        Args:
            message: Status message to dispatch
        """
        self.dispatch(Event(EventType.STATUS_UPDATED, message))
    
    def dispatch_error(self, error: str) -> None:
        """
        Convenience method to dispatch an error event.
        
        Args:
            error: Error message to dispatch
        """
        self.dispatch(Event(EventType.ERROR_OCCURRED, error))
    
    def dispatch_processing_started(self) -> None:
        """Dispatch a processing started event."""
        self.dispatch(Event(EventType.PROCESSING_STARTED))
    
    def dispatch_processing_completed(self, data: Any = None) -> None:
        """
        Dispatch a processing completed event.
        
        Args:
            data: Optional data associated with processing completion
        """
        self.dispatch(Event(EventType.PROCESSING_COMPLETED, data))
    
    def dispatch_note_saved(self, file_path: str) -> None:
        """
        Dispatch a note saved event.
        
        Args:
            file_path: Path to the saved note file
        """
        self.dispatch(Event(EventType.NOTE_SAVED, file_path))
