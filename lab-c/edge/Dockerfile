# Lab C's deliberately mis-configured nginx edge (server_tokens on, a public
# stub_status, autoindex on /static, the internal gateway proxied). The lab
# mounted default.conf and html/ from the repository; here they are part of the
# image, so a machine needs only the compose file. nginx is the lab's build,
# pinned by digest.
FROM nginx:1.25@sha256:a484819eb60211f5299034ac80f6a681b06f89e65866ce91f356ed7c72af059c
COPY default.conf /etc/nginx/conf.d/default.conf
COPY html /usr/share/nginx/html
