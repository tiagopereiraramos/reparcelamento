# Dockerfile para RPA com Chrome 136, ChromeDriver 136 e UC 3.4.7
FROM ubuntu:22.04

# 1. Instalar dependências básicas
RUN apt-get update && \
    apt-get install -y wget curl unzip gnupg2 ca-certificates python3 python3-pip python3-venv libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 libasound2 libxtst6 libxrandr2 libatk1.0-0 libgtk-3-0 && \
    rm -rf /var/lib/apt/lists/*

# 2. Instalar Google Chrome 136
RUN wget -O /tmp/google-chrome-136.deb "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_136.0.7103.93-1_amd64.deb" && \
    apt-get update && \
    apt-get install -y /tmp/google-chrome-136.deb && \
    rm /tmp/google-chrome-136.deb

# 3. Travar o Chrome para não atualizar
RUN apt-mark hold google-chrome-stable

# 4. Instalar ChromeDriver 136
RUN wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.93/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# 5. Instalar undetected-chromedriver 3.4.7 e dependências Python
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install undetected-chromedriver==3.4.7

# 6. Copiar o restante do código
COPY . /app
WORKDIR /app

# 7. Definir variáveis de ambiente para Chrome/Driver
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 8. Comando padrão (ajuste conforme seu entrypoint)
CMD ["python3", "seu_script_principal.py"] 