FROM node:20-slim

WORKDIR /app
COPY package.json .
RUN npm install --omit=dev
COPY . .

# Seed a couple of attachment files for the download endpoint.
RUN mkdir -p /srv/attachments \
    && echo "Q3 planning notes" > /srv/attachments/notes.txt \
    && echo "logo-bytes" > /srv/attachments/logo.png

ENV PORT=5002 FILES_ROOT=/srv/attachments
EXPOSE 5002
CMD ["node", "server.js"]
