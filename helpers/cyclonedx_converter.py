import datetime
import json
import os
import uuid


def save_cyclonedx(results, repo_path, output_path):
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "tools": [
                {
                    "vendor": "RepoScanner",
                    "name": "repository-scanner",
                    "version": "1.0.0"
                }
            ]
        },
        "components": []
    }

    for lang, lib, ver in results['dependencies']:
        # component_uuid = str(uuid.uuid4())

        component = {
            "type": "library",
            "bom-ref": f"pkg:{lang.lower()}/{lib}@{ver}",
            "name": lib,
            "version": ver,
            "purl": f"pkg:{lang.lower()}/{lib}@{ver}",
            "properties": [
                {
                    "name": "language",
                    "value": lang
                }
            ]
        }

        bom["components"].append(component)

    project_component = {
        "type": "application",
        "bom-ref": "project",
        "name": os.path.basename(repo_path) if repo_path.rstrip('/') else "unknown-project",
        "properties": []
    }

    for language, count in results['languages'].items():
        project_component["properties"].append({
            "name": f"files.language.{language.lower()}",
            "value": str(count)
        })

    bom["components"].insert(0, project_component)

    with open(output_path, 'w') as f:
        json.dump(bom, f, indent=2)
