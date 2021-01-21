import functools
from abc import ABC, abstractmethod
from typing import AnyStr, Dict, Callable, List

from bidict import bidict
from sortedcontainers import SortedDict

from components.collect_filter import WhitespaceFilter, AppendSpaceFilter, LineBreakFilter
from components.commit_handler import ICommitHandler
from components.sink import ISink, ScreenSink
from utils.logging_base import LoggingBase


class IDataStorage(ABC):  # Working area
    @abstractmethod
    def push_to_buffer(self, text: AnyStr) -> None:
        pass

    @abstractmethod
    def pop_buffer(self) -> None:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def revert(self) -> None:
        pass


class AbstractDataStorage(IDataStorage, LoggingBase, ABC):
    def __init__(self):
        super().__init__()
        self.sinks: Dict[AnyStr, ISink] = {}
        self.collect_filters: SortedDict[int, Callable[[AnyStr], AnyStr]] = SortedDict()
        self.collect_filters_priority_map: bidict[AnyStr, int] = bidict()
        self.commit_handlers: Dict[AnyStr, ICommitHandler] = {}

    def register_sink(self, sink_name: AnyStr,
                      sink: ISink) -> None:
        if sink_name in self.sinks.keys():
            raise RuntimeError('Duplicate sink name')
        self.sinks[sink_name] = sink

    def deregister_sink(self, sink_name: AnyStr) -> None:
        self.sinks.pop(sink_name)

    def on_committed_text_return(self, returned_text: AnyStr) -> None:
        for name, sink in self.sinks.items():
            self.logger.debug(f'Returned data processed by {name}.')
            sink.append_data(returned_text)

    def register_collect_filter(self, filter_name: AnyStr, priority: int,
                                collect_filter: Callable[[AnyStr], AnyStr]) -> None:
        if filter_name in self.collect_filters_priority_map.keys():
            raise RuntimeError('Duplicate filter name')
        self.collect_filters_priority_map[filter_name] = priority
        if priority in self.collect_filters.keys():
            raise RuntimeError('Duplicate filter priority')
        self.collect_filters[priority] = collect_filter

    def deregister_collect_filter(self, filter_name: AnyStr) -> None:
        index = self.collect_filters_priority_map.pop(filter_name)
        self.collect_filters.pop(index)

    def on_push_to_buffer(self, text: AnyStr) -> AnyStr:
        middle_value: AnyStr = text
        for index, collect_filter in self.collect_filters.items():
            self.logger.debug(f'Pushed data filtered by {self.collect_filters_priority_map.inverse.get(index)}.')
            middle_value = collect_filter(middle_value)
        return middle_value

    def register_commit_handler(self, commit_handler_name: AnyStr, commit_handler: ICommitHandler):
        if commit_handler_name in self.commit_handlers.keys():
            raise RuntimeError('Duplicate commit handler name')
        commit_handler.register_callback('default_callback',
                                         functools.partial(AbstractDataStorage.on_committed_text_return, self))
        self.commit_handlers[commit_handler_name] = commit_handler

    def deregister_commit_handler(self, commit_handler_name: AnyStr):
        self.commit_handlers.pop(commit_handler_name)

    def revert(self) -> None:
        for _, sink in self.sinks.items():
            sink.revert()


class MemoryDataStorage(AbstractDataStorage):
    def __init__(self):
        super().__init__()
        self.working_space: List[AnyStr] = []
        self.committed_data: List[AnyStr] = []

    def push_to_buffer(self, text: AnyStr) -> None:
        self.working_space.append(self.on_push_to_buffer(text))

    def pop_buffer(self) -> None:
        if len(self.working_space) > 0:
            self.working_space.pop()

    def commit(self) -> None:
        if len(self.working_space) == 0:
            return
        for commit_handler_name, commit_handler in self.commit_handlers.items():
            self.logger.debug(f'Commit handler {commit_handler_name} called.')
            commit_handler.commit(''.join(self.working_space))
        self.working_space.clear()


class DefaultZhMemoryDataStorage(MemoryDataStorage):
    def __init__(self):
        super().__init__()
        self.register_collect_filter('remove_white_space', 0, WhitespaceFilter.filter)
        self.register_collect_filter('remove_line_break', 1, LineBreakFilter.filter)


class DefaultEnMemoryDataStorage(MemoryDataStorage):
    def __init__(self):
        super().__init__()
        self.register_collect_filter('remove_line_break', 0, LineBreakFilter.filter)
        self.register_collect_filter('append_space', 1, AppendSpaceFilter.filter)
