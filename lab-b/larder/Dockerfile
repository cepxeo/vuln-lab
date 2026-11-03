# ---- build the React (Vite) frontend ----
FROM node:20 AS web
WORKDIR /web
COPY frontend/package.json frontend/package.json
WORKDIR /web/frontend
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- backend (node:20 full image has the toolchain better-sqlite3 needs) ----
FROM node:20
WORKDIR /app
COPY backend/package.json .
RUN npm install
COPY backend/ .
# React build output served as the API's static root
COPY --from=web /web/frontend/dist ./public
EXPOSE 5020
CMD ["node", "server.js"]
