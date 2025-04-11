import os
from typing import Dict, List, Tuple

from consts.file_extensions import LANGUAGE_EXTENSIONS
from parsers import *


class RepositoryScanner:

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._language_counters = {}
        self._dependencies = []

    def scan_languages(self) -> Dict[str, int]:
        self._language_counters = {}

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()

                for language, extensions in LANGUAGE_EXTENSIONS.items():
                    if file_ext in extensions:
                        self._language_counters[language] = self._language_counters.get(language, 0) + 1
                        break

        return self._language_counters

    def get_language_parsers(self):
        parsers = {}

        if 'Python' in self._language_counters:
            parsers['Python'] = PythonParser(self.repo_path)

        if 'JavaScript' in self._language_counters:
            parsers['JavaScript'] = JavaScriptParser(self.repo_path)

        if 'Java' in self._language_counters:
            parsers['Java'] = JavaParser(self.repo_path)

        if 'C++' in self._language_counters:
            parsers['C++'] = CppParser(self.repo_path)

        if 'C#' in self._language_counters:
            parsers['C#'] = CSharpParser(self.repo_path)

        if 'Go' in self._language_counters:
            parsers['Go'] = GoParser(self.repo_path)

        if 'Rust' in self._language_counters:
            parsers['Rust'] = RustParser(self.repo_path)

        if 'PHP' in self._language_counters:
            parsers['PHP'] = PhpParser(self.repo_path)

        if 'Ruby' in self._language_counters:
            parsers['Ruby'] = RubyParser(self.repo_path)

        return parsers

    def scan_dependencies(self) -> List[Tuple[str, str, str]]:
        if not self._language_counters:
            self.scan_languages()

        parsers = self.get_language_parsers()

        self._dependencies = []
        for language, parser in parsers.items():
            dependencies = parser.get_dependencies()
            self._dependencies.extend(dependencies)

        return self._dependencies

    def get_results(self) -> Dict:

        return {
            'languages': self._language_counters,
            'dependencies': self._dependencies
        }
