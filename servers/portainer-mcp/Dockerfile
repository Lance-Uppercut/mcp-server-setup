FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git make

WORKDIR /app

RUN git clone --depth 1 --branch v0.7.0 https://github.com/portainer/portainer-mcp.git .

RUN go build -o portainer-mcp ./cmd/portainer-mcp

FROM alpine:latest

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/portainer-mcp .

ENV PORTAINER_SERVER=http://localhost:6500
ENV PORTAINER_TOKEN=

ENTRYPOINT ["/app/portainer-mcp"]
