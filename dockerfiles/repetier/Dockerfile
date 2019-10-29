FROM resin/rpi-raspbian

LABEL maintainer="andreas@jungierek.de"
LABEL version="v0.92.3"

ADD http://download.repetier.com/files/server/debian-armhf/Repetier-Server-0.92.3-Linux.deb repetier-server.deb

RUN dpkg --unpack repetier-server.deb \
    && rm -rf repetier-server.deb \
    && rm -f /var/lib/dpkg/info/repetier-server.postinst

EXPOSE 3344    

CMD [ "/usr/local/Repetier-Server/bin/RepetierServer", "-c", "/usr/local/Repetier-Server/etc/RepetierServer.xml" ]
