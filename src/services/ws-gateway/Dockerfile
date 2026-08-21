FROM golang:1.25-alpine AS builder

WORKDIR /code

copy go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /code/ws-gateway ./cmd/main.go

FROM alpine:3.20

WORKDIR /code

RUN apk --no-cache add ca-certificates

COPY --from=builder /code/ws-gateway .

EXPOSE 4333

CMD [ "./ws-gateway" ]