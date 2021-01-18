from abc import ABC, abstractmethod
from typing import AnyStr, Callable, Dict
import translators
import threading
from utils.logging_base import LoggingBase


class ICommitHandler(ABC):
    @abstractmethod
    def commit(self, data: AnyStr) -> None:
        pass

    @abstractmethod
    def register_callback(self, callback_name: AnyStr, callback: Callable[[AnyStr], None]):
        pass

    @abstractmethod
    def deregister_callback(self, callback_name: AnyStr):
        pass


class AbstractCommitHandler(ICommitHandler, LoggingBase, ABC):
    def __init__(self):
        super().__init__()
        self.callbacks: Dict[AnyStr, Callable[[AnyStr], None]] = {}

    def register_callback(self, callback_name: AnyStr, callback: Callable[[AnyStr], None]):
        if callback_name in self.callbacks.keys():
            raise RuntimeError('Duplicate callback name')
        self.callbacks[callback_name] = callback

    def deregister_callback(self, callback_name: AnyStr):
        self.callbacks.pop(callback_name)


class TransparentCommitHandler(AbstractCommitHandler):
    def commit(self, data: AnyStr) -> None:
        for callback_name, callback in self.callbacks.items():
            self.logger.debug(f'Callback {callback_name} invoked.')
            callback(data)


class GoogleTranslationCommitHandler(AbstractCommitHandler):
    def commit(self, data: AnyStr) -> None:
        self.logger.debug('Async invoke translator.')
        thread = threading.Thread(target=lambda: self.work(data))
        thread.start()

    def work(self, data: AnyStr):
        result = translators.google(query_text=data,to_language='zh-CN')
        for callback_name, callback in self.callbacks.items():
            self.logger.debug(f'Callback {callback_name} invoked.')
            callback(result)
