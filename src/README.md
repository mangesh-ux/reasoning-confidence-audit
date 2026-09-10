# Reusable instrumentation

`rebuild_public_results.py` is a standard-library-only result-packaging
instrument. It reads compact public inputs or Q3–Q7 aggregate JSON from a
separate frozen artifact tree, records source hashes, and writes the public
summary schema.

It is intentionally not a model runner. It does not load weights, start a
server, generate tokens, modify CoDE-Stop, select a threshold, or alter frozen
artifacts. The 5–10 minute public verification path is described in the root
[README](../README.md).
