# The vulnerability zoo as a container: small vulnerable apps, each with a safe
# twin, served by one standard-library Python process (app/, a copy of the
# modules the zoo server needs; zoo/sync.sh keeps it current).
#
#   ZOO_PROFILE  smoke (6 apps on ZOO_PORT, their safe twins 50 above) or all
#                (20 apps on 9100-9119, twins on 9150-9169)
#   ZOO_PORT     the first port (smoke only; the safe origin is ZOO_PORT + 50)
#   ZOO_ADDRESS  the address the scanner reaches this host at: it goes into
#                /out/zoo.yaml (the ground truth) and /out/targets.txt
FROM python:3.12-slim
WORKDIR /zoo
COPY app/ /zoo/
RUN mkdir -p /out
ENV ZOO_PROFILE=smoke ZOO_PORT=9100 ZOO_ADDRESS="" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 9100-9119 9150-9169
ENTRYPOINT ["sh", "-c", "if [ -z \"$ZOO_ADDRESS\" ]; then echo 'Set ZOO_ADDRESS to the address the scanner reaches this host at.' >&2; exit 2; fi; exec python -m authorization_tests.vulnzoo.serve --profile \"$ZOO_PROFILE\" --bind 0.0.0.0 --port \"$ZOO_PORT\" --address \"$ZOO_ADDRESS\" --truth /out/zoo.yaml --targets /out/targets.txt"]
