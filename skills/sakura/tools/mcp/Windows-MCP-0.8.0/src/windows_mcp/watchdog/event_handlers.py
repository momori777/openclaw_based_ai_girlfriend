from windows_mcp.uia.core import _AutomationClient
import comtypes
import logging
import weakref

# Get UIA Interface for COM definitions
uia_client = _AutomationClient.instance()
UIA = uia_client.UIAutomationCore

logger = logging.getLogger(__name__)

class FocusChangedEventHandler(comtypes.COMObject):
    _com_interfaces_ = [UIA.IUIAutomationFocusChangedEventHandler]

    def __init__(self, parent):
        self._parent = weakref.ref(parent)
        super(FocusChangedEventHandler, self).__init__()

    def HandleFocusChangedEvent(self, sender):
        try:
            parent = self._parent()
            if parent and parent._focus_callback:
                parent._focus_callback(sender)
        except comtypes.COMError as e:
            logger.debug("Focus callback COM error: %s", e)
        except Exception as e:
            logger.debug("Focus callback error: %s", e)
        return 0  # S_OK


class StructureChangedEventHandler(comtypes.COMObject):
    _com_interfaces_ = [UIA.IUIAutomationStructureChangedEventHandler]

    def __init__(self, parent):
        self._parent = weakref.ref(parent)
        super(StructureChangedEventHandler, self).__init__()

    def HandleStructureChangedEvent(self, sender, changeType, runtimeId):
        try:
            parent = self._parent()
            if parent and parent._structure_callback:
                parent._structure_callback(sender, changeType, runtimeId)
        except comtypes.COMError as e:
            logger.debug("Structure callback COM error: %s", e)
        except Exception as e:
            logger.debug("Structure callback error: %s", e)
        return 0  # S_OK


class PropertyChangedEventHandler(comtypes.COMObject):
    _com_interfaces_ = [UIA.IUIAutomationPropertyChangedEventHandler]

    def __init__(self, parent):
        self._parent = weakref.ref(parent)
        super(PropertyChangedEventHandler, self).__init__()

    def HandlePropertyChangedEvent(self, sender, propertyId, newValue):
        try:
            parent = self._parent()
            if parent and parent._property_callback:
                parent._property_callback(sender, propertyId, newValue)
        except comtypes.COMError as e:
            logger.debug("Property callback COM error: %s", e)
        except Exception as e:
            logger.debug("Property callback error: %s", e)
        return 0  # S_OK
