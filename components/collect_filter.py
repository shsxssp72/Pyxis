import re
from typing import AnyStr


class WhitespaceFilter(object):
    @staticmethod
    def filter(input_text: AnyStr) -> AnyStr:
        result = re.sub(r'\s', '', input_text)
        return result


class LineBreakFilter(object):
    @staticmethod
    def filter(input_text: AnyStr) -> AnyStr:
        result = re.sub(r'-(\r)?\n', '', input_text)
        result = re.sub(r'(\r)?\n', ' ', result)
        return result


class AppendSpaceFilter(object):
    @staticmethod
    def filter(input_text: AnyStr) -> AnyStr:
        result = re.sub(r'\.\s*', '. ', input_text)
        return result
