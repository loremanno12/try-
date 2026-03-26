# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copia package files
COPY package*.json ./

# Installa dipendenze
RUN npm ci

# Copia codice sorgente
COPY . .

# Build produzione
RUN npm run build

# Production stage
FROM nginx:alpine

# Rimuovi config default nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia build output
COPY --from=build /app/dist /usr/share/nginx/html

# Copia configurazione nginx personalizzata
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Esposizione porta
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
