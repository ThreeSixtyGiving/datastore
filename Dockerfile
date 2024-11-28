FROM python:3.8.16-buster

RUN mkdir /code
WORKDIR /code/
COPY requirements_dev.txt /code/requirements_dev.txt
RUN python -m venv /ve && . /ve/bin/activate && pip install --upgrade setuptools pip wheel
RUN . /ve/bin/activate && pip install -r requirements_dev.txt

EXPOSE 8000
