FROM python:3.5

MAINTAINER AHAPX
MAINTAINER anarchy.b@gmail.com

RUN git clone https://github.com/AHAPX/websocket.git /websocket
RUN pip install -r /websocket/requirements.txt

CMD cd /websocket && python websocket.py -c config.cfg

