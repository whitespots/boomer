import os
from abc import ABC, abstractmethod
from typing import List, Tuple


class Parser(ABC):

    def __init__(self, repo_path: str, only_direct=False, prefer_locks=False):
        self.repo_path = repo_path
        self.language = self.__class__.__name__.replace('Parser', '')
        self.only_direct = only_direct
        self.prefer_locks = prefer_locks

    @abstractmethod
    def find_dependency_files(self) -> List[str]:
        pass

    @abstractmethod
    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        pass

    def get_dependencies(self) -> List[Tuple[str, str, str, str]]:
        dependency_files = self.find_dependency_files()
        all_dependencies = []

        for file_path in dependency_files:
            dependencies = self.parse_dependencies(file_path)
            source_file = os.path.basename(file_path)
            for dependency in dependencies:
                language, library, version, *metadata = dependency
                all_dependencies.append(
                    (language, library, version, source_file, *metadata)
                )

        return all_dependencies
