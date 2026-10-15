"""Declared changes of v1.4.0-gh, v1.4.1-gh and v1.4.2-gh to files of frozen phases (shared by the regression tests; not a test module).

Cambios declarados de v1.4.0-gh en archivos de fases congeladas (compartido por las pruebas de regresión).

Code and configuration files are pinned to their exact new hash, together with the hash they had in v1.3.1-f3, so
any further change is still detected. Documentation files are declared by description only.
"""
from __future__ import annotations

# path -> (hash in v1.3.1-f3 and earlier phases, authorised hash in v1.4.0-gh, change)
GH_PINNED = {
    "src/generate_data.py": ("196e6c320d2bef31ac8297969ffe88371ebe825f689ff06347d90525b00d0c10",
                             "3a6a869c806a13901344e66837e9e4356b202924802af1270e154090b143164e",
                             'line-ending fix: lineterminator="\\n" in the three CSV writes (same bytes on Linux)'),
    "scripts/build_notebook.py": ("579d547a100d7db9da047dff699ec57bbd6ce05c7c430b0442f62baa31583192",
                                  "aa00e6c9aadf7edbe8e99489ae9c954a43f16a6bb84c466cdd078258b99826cb",
                                  'line-ending fix (v1.4.0-gh) and reference chart rendering applied in the kernel (v1.4.1-gh); '
                                  'cells unchanged, same notebook bytes as F1'),
    ".gitignore": ("b9e0ad01d09ecce26efceded3c4bfd97ef64d6cddd812a1ad933c3949e9c31d7",
                   "acd311ef94d80400f420b6587f28479f46e1aacd9d42f492b23014eb8e3a4006",
                   "virtual environments, secrets, local copies, editors and build/ added; original four rules kept"),
    "scripts/f3_run.py": ("9b5c4a9ad80fc7896869327851e17094e0daa0b9d062447c36e8339de30cfba7",
                          "ff5e7a8a234a231c369fde25597c970b2f375ca092c26f47d030346a07f5068a",
                          "guard only: refuses to run on this tree (reports/f3/ is frozen)"),
    # v1.4.2-gh, authorised compatibility fix found on Windows: one line of test_regeneration_is_reproducible
    "tests/test_integrity.py": ("4613de2b419251b3bb26ebf05a643e70ef7b2678f343c29286c2dd1895776f77",
                                "65a60448d4e51e00fb59d0d4865f73ba1adc6e36dac12a55923e9e51acb69c13",
                                'compatibility fix: the temporary CSV is written with lineterminator="\\n"; '
                                'the byte-for-byte comparison with data/ is unchanged'),
}
GH_DOCS = {
    "README.md": "rewritten for visitors; phase history moved to links",
    "README.es.md": "reescrito para visitantes; historial de fases enlazado",
    "docs/PROJECT_STATUS.md": "v1.4.0-gh state, decisions and open items",
    "docs/PROJECT_STATUS.es.md": "estado, decisiones y pendientes de v1.4.0-gh",
}
GH_TESTS = {
    "tests/test_regression_f0.py": "recognises the declared v1.4.0-gh changes",
    "tests/test_regression_f1.py": "recognises the declared v1.4.0-gh changes",
    "tests/test_regression_f2.py": "recognises the declared v1.4.0-gh changes",
}
GH_DECLARED_MODIFIED = {**{k: v[2] for k, v in GH_PINNED.items()}, **GH_DOCS, **GH_TESTS}
