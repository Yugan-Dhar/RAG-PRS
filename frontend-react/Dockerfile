FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy all frontend files
COPY . .

# Expose Vite port
EXPOSE 5173

# Run vite server and expose to host
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
