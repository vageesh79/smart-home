"""Define a registry for all AppDaemon timer handles."""

# pylint: disable=too-many-arguments,attribute-defined-outside-init

import uuid

import appdaemon.plugins.hass.hassapi as hass


class HandlerRegistry(hass.Hass):
    """Define a class to handle a collection of AppDaemon handles."""

    # --- INITIALIZERS --------------------------------------------------------
    def initialize(self) -> None:
        """Initialize."""
        self._handles = {}  # type: ignore
        self.cancel_timer_methods = []  # type: ignore

    # --- HELPERS -------------------------------------------------------------
    def __contains__(self, key: str) -> bool:
        """Determine if a key exists in registry."""
        return self._handles.__contains__(key)

    def _cancel_timer(self, handle: uuid.UUID) -> None:
        """Get around AppDaemon by redefining what _cancel_timer does."""
        for method in self.cancel_timer_methods:
            method(handle)

    # --- APP API -------------------------------------------------------------
    def deregister(self, *keys: str, cancel: bool = True) -> None:
        """Deregister a notification"""
        for key in keys:
            if key not in self._handles:
                self.log('Cannot deregister unregistered notification: "{0}"'.
                         format(key))
                continue

            handles = self._handles[key]
            if isinstance(handles, str):
                handles = [handles]

            for handle in handles:
                if cancel:
                    self._cancel_timer(handle)
            del self._handles[key]

    def deregister_all(self, cancel: bool = True) -> None:
        """Deregister all notifications."""
        if cancel:
            for handle in self._handles.values():
                self._cancel_timer(handle)

        self._handles.clear()

        self.log('All handlers deregistered: {0}'.format(self._handles))

    def register(self, key: str, *handles: uuid.UUID) -> None:
        """Register a new notification."""
        if key in self._handles:
            self.log(
                'Replacing existing notification: "{0}"'.format(key),
                level='WARNING')
            for handle in handles:
                self._cancel_timer(handle)

        self._handles[key] = handles

        self.log('Handler added: {0}'.format(self._handles))
