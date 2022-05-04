FROM python:3-slim

ARG DATA_FILE

WORKDIR /usr/src/app

COPY data/${DATA_FILE} ./data.csv

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt 2> /dev/null

COPY smart-meter.py .

ARG BACKEND_HOST

RUN sed -i "s/host_placeholder/${BACKEND_HOST}/" smart-meter.py

CMD ["python", "smart-meter.py"]