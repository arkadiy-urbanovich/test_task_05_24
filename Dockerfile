FROM python:3.12.3
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-deps -r requirements.txt
