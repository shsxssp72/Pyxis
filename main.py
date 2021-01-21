import argparse
import json
import logging
import time
from typing import AnyStr, Dict

from components.commit_handler import GoogleTranslationCommitHandler, translation_providers
from components.data_storage import DefaultZhMemoryDataStorage, AbstractDataStorage, DefaultEnMemoryDataStorage
from components.event_handler import DefaultEventHandler, IEventHandler
from components.event_listener import KeyboardEventListener, IEventListener
from components.sink import ScreenSink, FileSink
from utils.logging_base import LoggingBase


class Core(LoggingBase):
    def __init__(self, config: Dict):
        super().__init__()
        self.config: Dict = config
        if config['source-language'] == 'zh':
            self.data_storage: AbstractDataStorage = DefaultZhMemoryDataStorage()
        else:
            self.data_storage: AbstractDataStorage = DefaultEnMemoryDataStorage()
        if not config['no-result-to-screen']:
            self.data_storage.register_sink('screen_sink', ScreenSink())
        if config['output-file'] is not None:
            self.data_storage.register_sink('file_sink', FileSink(config['output_file']))

        self.data_storage.register_commit_handler(commit_handler_name=config['translation-provider'],
                                                  commit_handler=translation_providers.get(
                                                      config['translation-provider'].lower())(
                                                      target_language=config['target-language']))
        self.event_handler: IEventHandler = DefaultEventHandler(data_storage=self.data_storage)
        self.event_listener: IEventListener = KeyboardEventListener(key_bindings=self.config['key-bindings'],
                                                                    event_handler=self.event_handler)
        self.event_listener.start()

    def main_loop(self):
        try:
            while not time.sleep(60):
                pass
        except KeyboardInterrupt:
            confirm = input('Quit?')
            if confirm.lower() == 'y':
                pass
            else:
                self.main_loop()


def load_config(config_file_path: AnyStr):
    with open(config_file_path, 'r')as config_input:
        config_json = config_input.read()
    return json.loads(config_json)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-result-to-stdout', dest='no_result_to_screen', action='store_true')
    parser.add_argument('-L', '--log-level', dest='log_level', type=str, default="WARNING")
    parser.add_argument('-s', '--source-language', dest='source_language', type=str, default="en")
    parser.add_argument('-t', '--target-language', dest='target_language', type=str, default="zh")
    parser.add_argument('-p', '--translation-provider', dest='translation_provider', type=str, default="google")
    parser.add_argument('-o', '--output', dest='output_file', type=str)
    parser.add_argument('-c', '--config', dest='config_file', type=str, default="config.json")
    args = parser.parse_args()

    app_config: Dict = load_config(config_file_path=args.config_file)
    app_config['no-result-to-screen'] = args.no_result_to_screen
    app_config['log-level'] = args.log_level
    app_config['source-language'] = args.source_language
    app_config['target-language'] = args.target_language
    app_config['translation-provider'] = args.translation_provider
    app_config['output-file'] = args.output_file

    logging.basicConfig(level=app_config['log-level'],
                        format='[%(levelname)s][%(asctime)s][%(threadName)s][%(name)s]: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    core = Core(config=app_config)
    core.main_loop()
