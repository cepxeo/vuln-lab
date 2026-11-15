# Stagehand (Lab E): React 18 + Vite in front of Node 22 + Express, one container.
# Deliberately vulnerable benchmark target (GROUND_TRUTH-r5.md).
#
# The comments that explain the planted flaws stay in the repository. Both
# stages remove them from the image: the client source is served in the source
# maps (E1) and the server source is readable through the file-read flaws, and
# neither must give the other answers away.

# ---- build the React (Vite) frontend ----
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json .
RUN npm install
COPY frontend/ .
RUN find src vite.config.js -type f -exec sed -i -E \
      -e '/^[[:space:]]*\/\/( |$)/d' -e '/^[[:space:]]*\{\/\*.*\*\/\}[[:space:]]*$/d' {} + \
    && npm run build

# ---- API + static build (no native modules: builds for amd64 and arm64) ----
FROM node:22-alpine
# qrencode renders the ticket QR codes. The extra passwd line is the canary of
# the layout traversal (E8).
RUN apk add --no-cache libqrencode-tools \
    && echo 'stagehand:x:1500:1500:SH-E08-90cb2f58:/app:/sbin/nologin' >> /etc/passwd
WORKDIR /app
COPY backend/package.json .
RUN npm install --omit=dev
COPY backend/ .
RUN find . -path ./node_modules -prune -o -name '*.js' -exec sed -i -E '/^[[:space:]]*\/\/( |$)/d' {} +
# React build output (with its source maps) served as the API's static root
COPY --from=web /web/dist ./public
# MAIL_RELAY_TOKEN is the canary of the template injection (E14).
ENV PORT=5050 MAIL_RELAY_TOKEN=SH-E14-a93c6d70
EXPOSE 5050
CMD ["node", "server.js"]
