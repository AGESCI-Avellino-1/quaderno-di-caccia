# syntax=docker/dockerfile:1
# QdC PWA served by nginx, which also forwards the Django paths to the "web" service,
# so app and API share one origin (session cookie + CSRF, no CORS).

# Built from the repository root (compose.prod.yml), to read the logos in resources/.
FROM node:26-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY resources/ /app/resources/
# The group's own logo (DEC-294), a path from the repository root; empty = AGESCI.
ARG QDC_LOGO=""
# Under the app's name on the start screen (DEC-332); empty = nothing.
ARG QDC_NOME_AVVIO=""
RUN QDC_LOGO="$QDC_LOGO" QDC_NOME_AVVIO="$QDC_NOME_AVVIO" npm run build

FROM nginx:stable-alpine
# The official image renders /etc/nginx/templates/*.template into conf.d at start-up.
COPY frontend/docker/default.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/docker/qdc-locations.conf frontend/docker/qdc-sicurezza.conf /etc/nginx/qdc/
COPY --from=build /app/frontend/dist /usr/share/nginx/html
