"""The vulnerability zoo (docs/plans/ai-pentest-synthetic-tests.md, layer L1).

Generic vulnerable handlers, each with a safe twin, served by a stdlib HTTP
server on 127.0.0.1:0, and the engine modules that should find them driven
against both over the real HTTP path. The cases are data (cases.py); the
runner is test_ai_pentest_zoo.py; the coverage rule is in
test_ai_pentest_zoo_coverage.py.
"""
