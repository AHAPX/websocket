FROM python:3.5

MAINTAINER AHAPX
MAINTAINER anarchy.b@gmail.com

RUN git clone https://github.com/AHAPX/websocket.git /websocket
RUN pip install -U pip
RUN pip install -r /websocket/requirements.txt

VOLUME /websocket
WORKDIR /websocket
EXPOSE 9999

CMD python websocket.py -c config.cfg
