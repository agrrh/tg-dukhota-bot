FROM python:3.10-alpine

WORKDIR /app

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY ./ ./

ENV PYTHONUNBUFFERED true
ENV PYTHONHASHSEED 0

CMD ["python", "main.py"]
