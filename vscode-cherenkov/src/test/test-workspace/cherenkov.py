import sys
import json

def main():
    if "--output-format" in sys.argv and "sarif" in sys.argv:
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "CHERENKOV",
                            "rules": [
                                {
                                    "id": "POST /payments"
                                }
                            ]
                        }
                    },
                    "results": [
                        {
                            "ruleId": "POST /payments",
                            "message": {
                                "text": "Missing field 'amount'"
                            },
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": { "uri": "mock-spec.yaml" },
                                        "region": { "startLine": 9 }
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        print(json.dumps(sarif))

if __name__ == "__main__":
    main()
