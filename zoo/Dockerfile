# The vulnerability zoo (tools/zoo/README.md, tier 3) as a container: the apps
# of services/server/authorization_tests/vulnzoo, the code the unit suite tests,
# served by its standard-library server. Build context: services/server
# (compose and build.sh pass it), so the image is always the tested zoo.
#
#   ZOO_PROFILE  smoke (6 apps on ZOO_PORT, their safe twins 50 above) or all
#                (20 apps on 9100-9119, twins on 9150-9169)
#   ZOO_PORT     the first port (smoke only; the safe origin is ZOO_PORT + 50)
#   ZOO_ADDRESS  the address the scanner reaches this host at: it goes into
#                /out/zoo.yaml (the bench ground truth) and /out/targets.txt
FROM python:3.12-slim
WORKDIR /zoo
COPY authorization_tests/__init__.py authorization_tests/__init__.py
COPY authorization_tests/vulnzoo authorization_tests/vulnzoo
RUN mkdir -p /out
ENV ZOO_PROFILE=smoke ZOO_PORT=9100 ZOO_ADDRESS="" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 9100-9119 9150-9169
ENTRYPOINT ["sh", "-c", "if [ -z \"$ZOO_ADDRESS\" ]; then echo 'Set ZOO_ADDRESS to the address the scanner reaches this host at.' >&2; exit 2; fi; exec python -m authorization_tests.vulnzoo.serve --profile \"$ZOO_PROFILE\" --bind 0.0.0.0 --port \"$ZOO_PORT\" --address \"$ZOO_ADDRESS\" --truth /out/zoo.yaml --targets /out/targets.txt"]
