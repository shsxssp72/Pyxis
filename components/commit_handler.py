from abc import ABC, abstractmethod
from typing import AnyStr, Callable, Dict, Set
import translators
import threading
from utils.logging_base import LoggingBase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


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
    # kwargs: Make compatible with AsyncTranslationCommitHandler
    def __init__(self, **kwargs):
        super().__init__()

    def commit(self, data: AnyStr) -> None:
        for callback_name, callback in self.callbacks.items():
            self.logger.debug(f'Callback {callback_name} invoked.')
            callback(data)


class AsyncTranslationCommitHandler(AbstractCommitHandler):
    class TranslatorReadyNoticeDecorator(object):
        def __init__(self, cls):
            self.cls = cls

        def __call__(self, source_language: AnyStr, target_language: AnyStr):
            entity: AsyncTranslationCommitHandler = self.cls(source_language, target_language)
            entity.logger.info(f'{entity.__class__.__name__} ready')
            return entity

    def __init__(self, source_language: AnyStr, target_language: AnyStr):
        super().__init__()
        self.source_language: AnyStr = source_language
        self.target_language: AnyStr = target_language

    def commit(self, data: AnyStr) -> None:
        self.logger.debug('Async invoke translator.')
        thread = threading.Thread(target=lambda: self.work(data))
        thread.start()

    def work(self, data: AnyStr):
        result = self.translate(data=data)
        for callback_name, callback in self.callbacks.items():
            self.logger.debug(f'Callback {callback_name} invoked.')
            callback(result)

    @abstractmethod
    def translate(self, data: AnyStr) -> AnyStr:
        pass


@AsyncTranslationCommitHandler.TranslatorReadyNoticeDecorator
class GoogleTranslationCommitHandler(AsyncTranslationCommitHandler):
    def translate(self, data: AnyStr) -> AnyStr:
        if self.target_language == 'zh':
            to_language: AnyStr = 'zh-CN'
        else:
            to_language: AnyStr = 'en'
        return translators.google(query_text=data, to_language=to_language)


@AsyncTranslationCommitHandler.TranslatorReadyNoticeDecorator
class BingTranslationCommitHandler(AsyncTranslationCommitHandler):
    def translate(self, data: AnyStr) -> AnyStr:
        if self.target_language == 'zh':
            to_language: AnyStr = 'zh-Hans'
        else:
            to_language: AnyStr = 'en'
        return translators.bing(query_text=data, to_language=to_language)


@AsyncTranslationCommitHandler.TranslatorReadyNoticeDecorator
class BaiduTranslationCommitHandler(AsyncTranslationCommitHandler):
    def translate(self, data: AnyStr) -> AnyStr:
        if self.target_language == 'zh':
            to_language: AnyStr = 'zh'
        else:
            to_language: AnyStr = 'en'
        return translators.baidu(query_text=data, to_language=to_language)


@AsyncTranslationCommitHandler.TranslatorReadyNoticeDecorator
class TencentTranslationCommitHandler(AsyncTranslationCommitHandler):
    def translate(self, data: AnyStr) -> AnyStr:
        if self.target_language == 'zh':
            to_language: AnyStr = 'zh'
        else:
            to_language: AnyStr = 'en'
        return translators.tencent(query_text=data, to_language=to_language)


class HeadlessBrowserConfig(object):
    page_load_wait_secs: int = 5
    page_load_timeout_secs: int = 10


class HeadlessBrowserTranslationCommitHandler(AsyncTranslationCommitHandler, ABC):
    def __init__(self, source_language: AnyStr, target_language: AnyStr):
        super().__init__(source_language, target_language)
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.privatebrowsing.autostart", True)
        profile.set_preference('network.proxy.type', 0)
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Firefox(firefox_profile=profile, options=options)
        self.driver.implicitly_wait(HeadlessBrowserConfig.page_load_wait_secs)
        self.driver.set_page_load_timeout(HeadlessBrowserConfig.page_load_timeout_secs)
        self.wait = WebDriverWait(self.driver, HeadlessBrowserConfig.page_load_timeout_secs)


@AsyncTranslationCommitHandler.TranslatorReadyNoticeDecorator
class DeepLBrowserTranslationCommitHandler(HeadlessBrowserTranslationCommitHandler):
    available_language: Set[AnyStr] = {
        'auto', 'pl', 'de', 'ru',
        'fr', 'nl', 'pt', 'ja',
        'es', 'it', 'en', 'zh'
    }
    # TODO make this configurable
    # Prevent translating status
    word_count_policy: Dict = {
        'zh-en': (lambda x: len(x) * 1.2),
        'en-zh': lambda x: int(len(x.split()) * 0.7)
    }

    class WhetherTranslatedDetectorByLength(object):
        def __init__(self, locator, estimated_length: int):
            self.locator = locator
            self.estimated_length: int = estimated_length

        def __call__(self, driver):
            try:
                element_text: AnyStr = driver.find_element(*self.locator).get_attribute('value')
                if element_text is not None \
                        and element_text.strip() != '' \
                        and len(element_text) >= self.estimated_length:
                    return element_text
                else:
                    return False
            except:
                return False

    def __init__(self, source_language: AnyStr, target_language: AnyStr):
        super().__init__(source_language, target_language)
        self.driver.get("https://www.deepl.com/translator")
        self.targetLanguageBtn = self.driver.find_element_by_xpath(
            "//button[contains(@dl-test,'translator-target-lang-btn')]")
        self.inputLanguageBtn = self.driver.find_element_by_xpath("//button[contains(@dl-test,'translator-source-lang-btn')]")
        self.inputLanguageBtn.click()
        self.wait.until(expected_conditions.presence_of_element_located(
            (By.XPATH, '//div[contains(@dl-test,"translator-source-lang-list")]')))
        self.driver.find_element_by_xpath(
            f"//button[contains(@dl-test,'translator-lang-option-{self.source_language}')]").click()
        self.targetLanguageBtn.click()
        self.wait.until(expected_conditions.presence_of_element_located(
            (By.XPATH, '//div[contains(@dl-test,"translator-target-lang-list")]')))
        self.driver.find_element_by_xpath(
            f'//button[contains(@dl-test,"translator-lang-option-{self.target_language}")]').click()
        self.original_input = self.driver.find_element_by_xpath(
            '//textarea[contains(@dl-test,"translator-source-input")]')

    def translate(self, data: AnyStr) -> AnyStr:
        self.original_input.clear()
        self.original_input.send_keys(data)
        result = self.wait.until(self.WhetherTranslatedDetectorByLength(
            (By.XPATH, '//textarea[contains(@dl-test,"translator-target-input")]'),
            self.word_count_policy[f'{self.source_language}-{self.target_language}'](data)))
        self.original_input.clear()
        return result


translation_providers: Dict[AnyStr, ICommitHandler.__class__] = {
    'google': GoogleTranslationCommitHandler,
    'bing': BingTranslationCommitHandler,
    'baidu': BaiduTranslationCommitHandler,
    'tencent': TencentTranslationCommitHandler,
    'transparent': TransparentCommitHandler,
    'deepl': DeepLBrowserTranslationCommitHandler,
}
