# syntax=docker/dockerfile:1
# QdC PWA served by nginx, which also forwards the Django paths to the "web" service,
# so app and API share one origin (session cookie + CSRF, no CORS).

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine
# The official image renders /etc/nginx/templates/*.template into conf.d at start-up.
COPY docker/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker/qdc-locations.conf docker/qdc-sicurezza.conf /etc/nginx/qdc/
COPY --from=build /app/dist /usr/share/nginx/html
