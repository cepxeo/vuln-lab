FROM golang:1.22-bookworm AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -buildvcs=false -o /gateway .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /gateway /usr/local/bin/gateway
ENV PORT=5003
EXPOSE 5003
CMD ["gateway"]
