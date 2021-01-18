import functools
import inspect
from abc import ABC, abstractmethod
from typing import AnyStr, Dict

from pynput import keyboard

from components.data_storage import IDataStorage
from components.event_handler import IEventHandler
from utils.logging_base import LoggingBase


class IEventListener(ABC):
    @abstractmethod
    def start(self):
        pass


class AbstractEventListener(IEventListener, LoggingBase, ABC):
    def __init__(self, event_handler: IEventHandler):
        super().__init__()
        self.event_handler: IEventHandler = event_handler


class KeyboardEventListener(AbstractEventListener):
    def __init__(self, key_bindings: Dict[AnyStr, AnyStr], event_handler: IEventHandler):
        super().__init__(event_handler)
        self.keyboard_listener: keyboard.Listener = keyboard.GlobalHotKeys(
            {
                key_bindings[function_name]: functools.partial(getattr(event_handler, 'signal'), function_name) for
                function_name in map(lambda x: x[0],
                                     inspect.getmembers(IDataStorage,
                                                        inspect.isfunction))
            })

    def start(self):
        self.keyboard_listener.start()
