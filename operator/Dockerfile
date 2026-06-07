FROM golang:1.22-alpine AS builder
WORKDIR /workspace
COPY go.mod ./
RUN go mod download 2>/dev/null || true
COPY . .
RUN go mod tidy 2>/dev/null || true
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o manager main.go
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o k8s-run ./cmd/k8s-run/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
WORKDIR /
COPY --from=builder /workspace/manager .
COPY --from=builder /workspace/k8s-run .
USER 65532:65532
ENTRYPOINT ["/manager"]
