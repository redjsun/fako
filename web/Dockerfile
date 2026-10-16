FROM node:25-alpine

# Sem root dentro do container: a imagem já traz o usuário node
WORKDIR /app
RUN chown node:node /app
USER node

# npm ci instala exatamente o package-lock.json
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

COPY --chown=node:node . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
