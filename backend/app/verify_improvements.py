#!/usr/bin/env python3
"""Quick verification of key improvements"""

import asyncio
import logging
import sys
from pathlib import Path

from app.services.gemini_service import ConsolidatedGeminiService

sys.path.insert(0, str(Path(__file__).parent.parent))


logging.getLogger().setLevel(logging.WARNING)


# Key test cases that were failing
CRITICAL_TESTS = [
    ("Uhl Judy A Revocable Trust", "Judy", "Uhl", "trust"),
    ("Mills Edwin L & Gloria F Rev Trs", "Edwin", "Mills", "trust"),
    ("Birch Dale F Family Trust", "Dale", "Birch", "trust"),
    ("Smith John", "John", "Smith", "person"),
    ("Microsoft Corporation", "", "", "company"),
]


async def verify():
    """Quick verification test"""
    gemini = ConsolidatedGeminiService()

    print("\n" + "=" * 60)
    print("VERIFYING KEY IMPROVEMENTS")
    print("=" * 60)

    inputs = [test[0] for test in CRITICAL_TESTS]

    try:
        result = await gemini.parse_names_batch(inputs)

        if hasattr(result, "results"):
            results = result.results
            success_count = 0

            for i, (input_name, exp_first, exp_last, exp_type) in enumerate(
                CRITICAL_TESTS
            ):
                if i < len(results):
                    r = results[i]
                    first = r.first_name if hasattr(r, "first_name") else ""
                    last = r.last_name if hasattr(r, "last_name") else ""
                    entity = r.entity_type if hasattr(r, "entity_type") else ""

                    match = (
                        first == exp_first and last == exp_last and entity == exp_type
                    )
                    status = "✅" if match else "❌"

                    print(f"\n{input_name[:40]}")
                    print(f"  Got: F='{first}' L='{last}' T='{entity}' {status}")

                    if match:
                        success_count += 1
                    else:
                        print(
                            f"  Expected: F='{exp_first}' L='{exp_last}' T='{exp_type}'"
                        )

            accuracy = success_count / len(CRITICAL_TESTS) * 100
            print(f"\n{'=' * 60}")
            print(
                f"Result: {success_count}/{len(CRITICAL_TESTS)} correct ({accuracy:.0f}%)"
            )

            if accuracy >= 80:
                print("✅ IMPROVEMENTS WORKING!")
            else:
                print("⚠️ Some issues remain")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(verify())
