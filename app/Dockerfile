# Stage 1: build
FROM node:24.11.1 AS build

WORKDIR /app
COPY makefile .

# Install requirements
COPY package.json .
COPY package-lock.json .
RUN make install

# Build app
COPY . .
ARG KRT_IS_NEXT=0
ENV KRT_IS_NEXT=$KRT_IS_NEXT
RUN make build

# Stage 2: Serve with nginx
FROM ghcr.io/kibalabs/app-serve:latest
COPY --from=build /app/dist /usr/share/nginx/html
