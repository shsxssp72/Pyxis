import inspect
from abc import ABC, abstractmethod
from typing import AnyStr, Callable, Dict

import pyperclip

from components.data_storage import IDataStorage
from utils.logging_base import LoggingBase


class IEventHandler(ABC):  # Keyboard,sth else signal etc
    @abstractmethod
    def signal(self, message: AnyStr):
        pass


class AbstractEventHandler(IEventHandler, LoggingBase):
    def __init__(self) -> None:
        super().__init__()
        self.action_map: Dict[AnyStr, Callable[[], None]] = {}

    def signal(self, message: AnyStr):
        if message in self.action_map.keys():
            self.logger.debug(f'Signal {message} triggered.')
            self.action_map.get(message)()
        else:
            raise RuntimeError('No matching signal.')


class DefaultEventHandler(AbstractEventHandler):
    def __init__(self, data_storage: IDataStorage):
        super().__init__()
        self.action_map: Dict[AnyStr, Callable[[], None]] = \
            {
                function_name: getattr(data_storage, function_name) for
                function_name in map(lambda x: x[0],
                                     inspect.getmembers(IDataStorage,
                                                        inspect.isfunction))
            }
        # Patch IDataStorage.push_to_buffer
        self.action_map['push_to_buffer'] = lambda: data_storage.push_to_buffer(pyperclip.paste())
        self.data_storage = data_storage
