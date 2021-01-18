from abc import abstractmethod, ABC
from pathlib import Path
from typing import AnyStr, List

from utils.logging_base import LoggingBase


class ISink(ABC):
    @abstractmethod
    def append_data(self, data: AnyStr) -> None:
        pass

    @abstractmethod
    def revert(self) -> None:
        pass


class AbstractSink(ISink, LoggingBase, ABC):
    def __init__(self):
        super().__init__()


class ScreenSink(AbstractSink):
    def append_data(self, data: AnyStr) -> None:
        self.logger.debug('Sink data')
        print(data)

    def revert(self) -> None:
        self.logger.debug('Revert data')
        print('Revert last output')


class FileSink(AbstractSink):
    def __init__(self, file_path: AnyStr):
        super().__init__()
        self.file_path: AnyStr = file_path
        self.appended_length_stack: List[int] = []

    def append_data(self, data: AnyStr) -> None:
        mode='a' if Path(self.file_path).exists() else 'w'
        with open(file=self.file_path, mode=mode) as output:
            output.write(data)
            self.appended_length_stack.append(data.count('\n'))

    def revert(self) -> None:
        with open(file=self.file_path, mode='r') as input:
            lines = input.readlines()
        with open(file=self.file_path, mode='w') as output:
            for line in lines[:-self.appended_length_stack[-1]]:
                output.write(line + '\n')
            self.appended_length_stack.pop(-1)
