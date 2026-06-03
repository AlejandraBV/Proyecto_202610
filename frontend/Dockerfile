FROM node:20-alpine

WORKDIR /app

# Install dependencies only
COPY package*.json ./
RUN npm install

EXPOSE 3000

# docker-compose overrides this with: npm run dev
CMD ["npm", "run", "dev"]
