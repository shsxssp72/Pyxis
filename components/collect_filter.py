import re
from typing import AnyStr


class WhitespaceLineBreakFilter(object):
    @staticmethod
    def filter(input_text: AnyStr) -> AnyStr:
        result = re.sub(r'\s|\n', '', input_text)
        return result


class AppendSpaceFilter(object):
    @staticmethod
    def filter(input_text: AnyStr) -> AnyStr:
        return input_text + ' '
