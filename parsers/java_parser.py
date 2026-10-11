import os
import json
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class JavaParser(Parser):

    def __init__(self, repo_path: str, only_direct=False, prefer_locks=False):
        super().__init__(repo_path, only_direct, prefer_locks)
        self._dependency_relations = []

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        java_dep_files = DEPENDENCY_FILES['Java']

        for root, dirs, files in os.walk(self.repo_path):
            files = set(files)
            if self.prefer_locks:
                maven_file = next(
                    (name for name in ('lockfile.json', 'pom.xml') if name in files),
                    None,
                )
            else:
                maven_file = next(
                    (name for name in ('pom.xml', 'lockfile.json') if name in files),
                    None,
                )
            if maven_file:
                dependency_files.append(os.path.join(root, maven_file))

            for file in files:
                if file in ('pom.xml', 'lockfile.json'):
                    continue
                if file in java_dep_files or (file.endswith('.gradle') and file != '.gradle'):
                    dependency_files.append(os.path.join(root, file))
            if '.gradle' in java_dep_files and '.gradle' in dirs:
                dependency_files.append(os.path.join(root, '.gradle'))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "pom.xml":
            dependencies = self._parse_pom_xml(file_path)
        elif filename == "lockfile.json":
            dependencies = self._parse_maven_lock(file_path)
        elif filename.endswith('.gradle') or filename == '.gradle':
            dependencies = self._parse_gradle_file(file_path)

        return dependencies

    def _parse_pom_xml(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            namespaces = {'ns': 'http://maven.apache.org/POM/4.0.0'}
            tree = ET.parse(file_path)
            root = tree.getroot()

            if root.tag.startswith('{'):
                deps_elements = root.findall('.//ns:dependencies/ns:dependency', namespaces)
                if not deps_elements:
                    deps_elements = root.findall('.//dependencies/dependency')
            else:
                deps_elements = root.findall('.//dependencies/dependency')

            for dep in deps_elements:
                group_id = None
                artifact_id = None
                version = 'latest'

                if root.tag.startswith('{'):
                    group_id_elem = dep.find('./ns:groupId', namespaces)
                    artifact_id_elem = dep.find('./ns:artifactId', namespaces)
                    version_elem = dep.find('./ns:version', namespaces)
                else:
                    group_id_elem = dep.find('./groupId')
                    artifact_id_elem = dep.find('./artifactId')
                    version_elem = dep.find('./version')

                if group_id_elem is not None:
                    group_id = group_id_elem.text

                if artifact_id_elem is not None:
                    artifact_id = artifact_id_elem.text

                if version_elem is not None:
                    version = version_elem.text

                if group_id and artifact_id:
                    library = f"{group_id}:{artifact_id}"
                    dependencies.append(('Java', library, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_gradle_file(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            dependencies_block = re.search(r'dependencies\s*{(.*?)}', content, re.DOTALL)
            if dependencies_block:
                deps_content = dependencies_block.group(1)

                pattern1 = r'(?:implementation|api|compile|testImplementation|testCompile|runtimeOnly|compileOnly)\s+[\'"]([^:\'\"]+):([^:\'\"]+):([^\'\"]+)[\'"]'
                matches1 = re.finditer(pattern1, deps_content)
                for match in matches1:
                    group_id = match.group(1)
                    artifact_id = match.group(2)
                    version = match.group(3)
                    library = f"{group_id}:{artifact_id}"
                    dependencies.append(('Java', library, version))

                pattern2 = r'(?:implementation|api|compile|testImplementation|testCompile|runtimeOnly|compileOnly)\s+group:\s*[\'"]([^\'\"]+)[\'"],\s*name:\s*[\'"]([^\'\"]+)[\'"],\s*version:\s*[\'"]([^\'\"]+)[\'"]'
                matches2 = re.finditer(pattern2, deps_content)
                for match in matches2:
                    group_id = match.group(1)
                    artifact_id = match.group(2)
                    version = match.group(3)
                    library = f"{group_id}:{artifact_id}"
                    dependencies.append(('Java', library, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def get_dependency_relations(self):
        return self._dependency_relations

    def _parse_maven_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            seen_components = set()

            def visit(node, parent=None):
                if node.get('included') is False:
                    return

                group_id = node.get('groupId')
                artifact_id = node.get('artifactId')
                version = node.get('selectedVersion') or node.get('version')
                if not group_id or not artifact_id or not version:
                    return

                component = ('Java', f"{group_id}:{artifact_id}", str(version))
                if component not in seen_components:
                    seen_components.add(component)
                    dependencies.append(component)

                self._dependency_relations.append((parent, component))
                if self.only_direct:
                    return

                for child in node.get('children', []):
                    visit(child, component)

            for dependency in data.get('dependencies', []):
                visit(dependency)

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies
